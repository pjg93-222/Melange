//! Read-only, projected XLSX scanner. No classification or accounting rules live here.
use quick_xml::{events::Event, Reader};
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, fs::File, io::{self, BufRead, BufReader, BufWriter, Write}};
use zip::ZipArchive;

type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
const MAX_XML: u64 = 2_000_000_000;
const MAX_COLUMNS: usize = 16_384;

#[derive(Deserialize)]
struct Request { path: String, tables: Vec<TableRequest>, #[serde(default="row_limit")] max_rows: usize, #[serde(default)] payload_table: Option<String> }
fn row_limit() -> usize { 1_000_000 }
#[derive(Deserialize)]
struct TableRequest { name: String, header: usize, #[serde(default)] columns: Vec<String>, #[serde(default)] end_row: Option<usize> }
#[derive(Serialize, Default)]
struct Table { headers: Vec<String>, rows: Vec<Vec<Option<String>>>, note: String }
#[derive(Serialize)]
struct Response { protocol: u8, sheets: Vec<String>, tables: HashMap<String, Table> }

fn attribute(e: &quick_xml::events::BytesStart<'_>, key: &[u8]) -> Result<String> {
    for a in e.attributes() { let a=a?; if a.key.as_ref()==key { return Ok(a.unescape_value()?.into_owned()); } }
    Ok(String::new())
}
fn key(s: &str) -> String {
    let mut result=String::new(); let mut separator=false;
    for c in s.trim().chars() {
        if c.is_ascii_alphanumeric() { if separator && !result.is_empty() { result.push('_'); } result.push(c.to_ascii_lowercase()); separator=false; }
        else { separator=true; }
    }
    match result.as_str() { "sha_256"=>"sha256".into(), "verified_data_through_date"=>"verified_data_through".into(), _=>result }
}
fn column(reference: &str) -> Result<usize> {
    let mut value=0usize;
    for c in reference.bytes().take_while(|c|c.is_ascii_alphabetic()) {
        value=value.checked_mul(26).and_then(|v|v.checked_add((c.to_ascii_uppercase()-b'A'+1) as usize)).ok_or("Invalid XLSX column")?;
    }
    if value==0 || value>MAX_COLUMNS { return Err("Invalid XLSX cell reference".into()); }
    Ok(value-1)
}
fn xml_reader<'a>(archive: &'a mut ZipArchive<File>, name: &str) -> Result<Reader<BufReader<zip::read::ZipFile<'a>>>> {
    let file=archive.by_name(name)?;
    if file.size()>MAX_XML { return Err("Workbook XML exceeds the safe reading limit".into()); }
    Ok(Reader::from_reader(BufReader::new(file)))
}
fn shared_strings(archive: &mut ZipArchive<File>) -> Result<Vec<String>> {
    if !archive.file_names().any(|name| name=="xl/sharedStrings.xml") { return Ok(Vec::new()); }
    let mut reader=xml_reader(archive,"xl/sharedStrings.xml")?;
    let (mut buffer,mut values,mut text)=(Vec::new(),Vec::new(),String::new());
    let (mut in_text,mut phonetic)=(false,0usize);
    loop {
        match reader.read_event_into(&mut buffer)? {
            Event::Start(e) if e.local_name().as_ref()==b"si" => text.clear(),
            Event::Start(e) if e.local_name().as_ref()==b"rPh" => phonetic+=1,
            Event::Start(e) if e.local_name().as_ref()==b"t" => in_text=phonetic==0,
            Event::Text(e) if in_text => text.push_str(&e.unescape()?),
            Event::CData(e) if in_text => text.push_str(std::str::from_utf8(&e)?),
            Event::End(e) if e.local_name().as_ref()==b"t" => in_text=false,
            Event::End(e) if e.local_name().as_ref()==b"rPh" => phonetic=phonetic.saturating_sub(1),
            Event::End(e) if e.local_name().as_ref()==b"si" => values.push(text.clone()),
            Event::DocType(_)=>return Err("Document types are not allowed in workbook XML".into()),
            Event::Eof => break,
            _=>{}
        } buffer.clear();
    } Ok(values)
}
fn sheet_paths(archive: &mut ZipArchive<File>) -> Result<Vec<(String,String)>> {
    let mut links=HashMap::new();
    { let mut reader=xml_reader(archive,"xl/_rels/workbook.xml.rels")?; let mut buffer=Vec::new();
      loop { match reader.read_event_into(&mut buffer)? {
        Event::Start(e)|Event::Empty(e) if e.local_name().as_ref()==b"Relationship" => {
            if attribute(&e,b"TargetMode")?!="External" {
                let target=attribute(&e,b"Target")?;
                // Resolve relative package names, never filesystem paths.
                let source=if target.starts_with('/') { target.trim_start_matches('/').to_owned() } else { format!("xl/{target}") };
                let mut parts=Vec::new();
                for part in source.split('/') { match part { ""|"."=>{}, ".."=>{ if parts.pop().is_none() { return Err("Invalid worksheet target".into()); } }, _=>parts.push(part) } }
                links.insert(attribute(&e,b"Id")?,parts.join("/"));
            }
        }, Event::DocType(_)=>return Err("Document types are not allowed in workbook XML".into()), Event::Eof=>break, _=>{} } buffer.clear(); }
    }
    let mut reader=xml_reader(archive,"xl/workbook.xml")?; let mut buffer=Vec::new(); let mut sheets=Vec::new();
    loop { match reader.read_event_into(&mut buffer)? {
        Event::Start(e)|Event::Empty(e) if e.local_name().as_ref()==b"sheet" => {
            let name=attribute(&e,b"name")?; let id=attribute(&e,b"r:id")?;
            sheets.push((name,links.get(&id).ok_or("Worksheet relationship is missing")?.clone()));
        }, Event::DocType(_)=>return Err("Document types are not allowed in workbook XML".into()), Event::Eof=>break, _=>{} } buffer.clear(); }
    Ok(sheets)
}
fn read_table(archive: &mut ZipArchive<File>, path: &str, request: &TableRequest, strings: &[String], limit: usize) -> Result<Table> {
    let mut reader=xml_reader(archive,path)?;
    let mut buffer=Vec::new(); let mut table=Table::default();
    let (mut row_number,mut cell_column,mut row_count)=(0usize,0usize,0usize);
    let (mut cell_type,mut text)=(String::new(),String::new());
    let (mut capture,mut present,mut phonetic)=(false,false,0usize);
    let mut cells: HashMap<usize,Option<String>>=HashMap::new();
    let mut selected:Vec<usize>=Vec::new(); let mut header_seen=false;
    loop {
        match reader.read_event_into(&mut buffer)? {
            Event::Start(e) if e.local_name().as_ref()==b"row" => {
                row_number=attribute(&e,b"r")?.parse()?; cells.clear();
                if request.end_row.is_some_and(|end| row_number > end) { break; }
                if row_number>request.header { row_count+=1; if row_count>limit || row_number>limit+request.header { return Err("Report exceeds the local graph reading limit".into()); } }
            },
            Event::Start(e)|Event::Empty(e) if e.local_name().as_ref()==b"c" => {
                cell_column=column(&attribute(&e,b"r")?)?; cell_type=attribute(&e,b"t")?; text.clear(); present=false; capture=false;
            },
            Event::Start(e) if e.local_name().as_ref()==b"rPh" => phonetic+=1,
            Event::Start(e) if e.local_name().as_ref()==b"v" || e.local_name().as_ref()==b"t" => { capture=phonetic==0; present=true; },
            Event::Text(e) if capture => text.push_str(&e.unescape()?),
            Event::CData(e) if capture => text.push_str(std::str::from_utf8(&e)?),
            Event::End(e) if e.local_name().as_ref()==b"v" || e.local_name().as_ref()==b"t" => capture=false,
            Event::End(e) if e.local_name().as_ref()==b"rPh" => phonetic=phonetic.saturating_sub(1),
            Event::End(e) if e.local_name().as_ref()==b"c" => {
                let value=if !present { None } else if cell_type=="s" { Some(strings.get(text.parse::<usize>()?).ok_or("Invalid shared-string index")?.clone()) } else { Some(text.clone()) };
                if row_number<=request.header || selected.contains(&cell_column) { cells.insert(cell_column,value); }
            },
            Event::End(e) if e.local_name().as_ref()==b"row" => {
                if row_number==3 { table.note=cells.get(&0).cloned().flatten().unwrap_or_default(); }
                if row_number==request.header {
                    let end=cells.keys().max().copied().map(|v|v+1).unwrap_or(0);
                    for col in 0..end { let header=key(cells.get(&col).and_then(|v|v.as_deref()).unwrap_or(""));
                        if !header.is_empty() && (request.columns.is_empty() || request.columns.contains(&header)) { selected.push(col); table.headers.push(header); }
                    } header_seen=true;
                } else if row_number>request.header {
                    if !header_seen { return Err(format!("{}: header row is missing",request.name).into()); }
                    let row:Vec<_>=selected.iter().map(|col|cells.remove(col).flatten()).collect();
                    if row.iter().any(|v|v.as_ref().map(|s|!s.is_empty()).unwrap_or(false)) { table.rows.push(row); }
                }
            },
            Event::DocType(_)=>return Err("Document types are not allowed in workbook XML".into()),
            Event::Eof=>break,
            _=>{}
        } buffer.clear();
    }
    if !header_seen { return Err(format!("{}: header row is missing",request.name).into()); }
    Ok(table)
}
fn scan(request: Request) -> Result<Response> {
    if let Some(name)=&request.payload_table {
        if name!="transfer_paths" { return Err("Unsupported payload projection".into()); }
        return scan_transfers(&request.path);
    }
    if request.max_rows>1_000_000 || request.tables.len()>32 { return Err("Scanner request exceeds safe limits".into()); }
    let file=File::open(&request.path)?; let before=file.metadata()?;
    let mut archive=ZipArchive::new(file)?; let sheets=sheet_paths(&mut archive)?;
    let strings=if request.tables.is_empty() { Vec::new() } else { shared_strings(&mut archive)? };
    let mut tables=HashMap::new();
    for table in request.tables {
        if table.header==0 || table.header>100 { return Err("Invalid header row".into()); }
        if let Some((_,path))=sheets.iter().find(|(name,_)|name==&table.name) {
            tables.insert(table.name.clone(),read_table(&mut archive,path,&table,&strings,request.max_rows)?);
        }
    }
    let after=std::fs::metadata(&request.path)?;
    if before.len()!=after.len() || before.modified()?!=after.modified()? { return Err("Workbook changed during native scan".into()); }
    Ok(Response { protocol:1, sheets:sheets.into_iter().map(|(name,_)|name).collect(),tables })
}
// Stream the pinned report payload. Unrelated arrays never enter memory.
fn scan_transfers(path: &str) -> Result<Response> {
    use serde::de::{DeserializeSeed, MapAccess, SeqAccess, Visitor, IgnoredAny, Error};
    struct Paths;
    impl<'de> DeserializeSeed<'de> for Paths {
        type Value=Table;
        fn deserialize<D:serde::Deserializer<'de>>(self,d:D)->std::result::Result<Table,D::Error>{
            struct Rows;
            impl<'de> Visitor<'de> for Rows {
                type Value=Table;
                fn expecting(&self,f:&mut std::fmt::Formatter)->std::fmt::Result{f.write_str("transfer paths")}
                fn visit_seq<A:SeqAccess<'de>>(self,mut seq:A)->std::result::Result<Table,A::Error>{
                    let mut unique=HashMap::new();
                    while let Some(row)=seq.next_element::<serde_json::Value>()? {
                        if row["status"].as_str()==Some("candidate_committee"){continue;}
                        let scalar=|key:&str|->std::result::Result<String,A::Error>{match &row[key]{serde_json::Value::String(v)=>Ok(v.clone()),serde_json::Value::Number(v)=>Ok(v.to_string()),_=>Err(A::Error::custom(format!("Missing transfer {key}")))}};
                        let key=(scalar("cycle")?,scalar("source")?,scalar("destination")?);let amount=scalar("amount")?;
                        if let Some(old)=unique.insert(key,amount.clone()){if old!=amount{return Err(A::Error::custom("Conflicting repeated transfer paths"));}}
                    }
                    let mut rows:Vec<_>=unique.into_iter().map(|((cycle,source,destination),amount)|vec![Some(cycle),Some(source),Some(destination),Some(amount)]).collect();rows.sort();
                    Ok(Table{headers:vec!["cycle".into(),"source".into(),"destination".into(),"amount".into()],rows,note:String::new()})
                }
            }d.deserialize_seq(Rows)
        }
    }
    struct Payload;
    impl<'de> Visitor<'de> for Payload {
        type Value=Table;
        fn expecting(&self,f:&mut std::fmt::Formatter)->std::fmt::Result{f.write_str("report payload")}
        fn visit_map<A:MapAccess<'de>>(self,mut map:A)->std::result::Result<Table,A::Error>{
            let mut found=None;
            while let Some(key)=map.next_key::<String>()?{if key=="transfer_paths"{if found.is_some(){return Err(A::Error::custom("Duplicate transfer table"));}found=Some(map.next_value_seed(Paths)?);}else{map.next_value::<IgnoredAny>()?;}}
            found.ok_or_else(||A::Error::custom("Pinned report has no complete transfer paths"))
        }
    }
    let mut decoder=serde_json::Deserializer::from_reader(BufReader::new(File::open(path)?));
    let table=serde::Deserializer::deserialize_map(&mut decoder,Payload)?;decoder.end()?;
    Ok(Response{protocol:1,sheets:Vec::new(),tables:HashMap::from([("transfer_paths".into(),table)])})
}
fn main() {
    let stdin=io::stdin(); let mut stdout=BufWriter::new(io::stdout().lock());
    // One request per line, reusable process. Errors are data, never an empty result.
    for line in stdin.lock().lines() {
        let response=match line {
            Ok(line)=>match serde_json::from_str::<Request>(&line).map_err(Into::into).and_then(scan) {
                Ok(value)=>serde_json::to_value(value).unwrap(),
                Err(error)=>serde_json::json!({"protocol":1,"error":error.to_string()})
            }, Err(_)=>break
        };
        if serde_json::to_writer(&mut stdout,&response).is_err() || writeln!(stdout).is_err() || stdout.flush().is_err() { break; }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn columns_and_keys() {
        assert_eq!(column("A5").unwrap(),0); assert_eq!(column("XFD42").unwrap(),16383);
        assert!(column("XFE1").is_err()); assert!(column("5").is_err());
        assert_eq!(key(" Net Included Amount "),"net_included_amount");
    }
}
