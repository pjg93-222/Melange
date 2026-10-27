"""Local verifier acceleration; existing ZIP and tree checks stay authoritative.

No application is run. Windows handles deny modification/replacement of the
archive and approved extractor until inspection, extraction and verification end.
On failure the fresh staging directory is retained for the owning controller.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess


def require(value,message):
    if not value: raise ValueError(message)


def physical(file,directory=False):
    file=Path(file).absolute();info=file.lstat()
    require(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400,'Linked extraction path')
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode),'Unexpected extraction path type')
    require(os.path.normcase(str(file))==os.path.normcase(str(file.resolve(strict=True))),'Redirected extraction path')
    if not directory: require(info.st_nlink==1,'Hardlinked extraction input')
    return info


def same(first,second):
    return (first.st_dev,first.st_ino,first.st_size,first.st_mtime_ns)==(second.st_dev,second.st_ino,second.st_size,second.st_mtime_ns)


@contextmanager
def held_read(file):
    require(os.name=='nt','Native extraction requires Windows')
    import msvcrt
    file=Path(file).absolute();before=physical(file)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    kernel.CreateFileW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
    # GENERIC_READ, FILE_SHARE_READ only: readers/execution are allowed; writes,
    # deletion and replacement are denied while this handle remains alive.
    handle=kernel.CreateFileW(str(file),0x80000000,1,None,3,0x80,None)
    if handle==ctypes.c_void_p(-1).value: raise ctypes.WinError(ctypes.get_last_error())
    try: fd=msvcrt.open_osfhandle(handle,os.O_RDONLY|os.O_BINARY)
    except BaseException: kernel.CloseHandle(handle);raise
    with os.fdopen(fd,'rb') as stream:
        require(same(before,os.fstat(stream.fileno())) and same(before,physical(file)),'Extraction input changed before locking')
        yield stream
        require(same(before,os.fstat(stream.fileno())) and same(before,physical(file)),'Extraction input changed while held')


def held_digest(stream):
    stream.seek(0);value=hashlib.file_digest(stream,'sha256').hexdigest();stream.seek(0);return value


def node(client,expression,value,*arguments):
    result=subprocess.run(['node','-e',expression,str(client),*map(str,arguments)],input=json.dumps(value),text=True,encoding='utf-8',stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode: raise ValueError('Existing directory verifier refused native extraction: '+result.stderr[-3000:])
    require(len(result.stdout.encode('utf-8'))<=17*1024**2,'Oversized verifier result')
    return result.stdout


def extract(client,archive,destination,descriptor,tool,tool_sha256):
    client,archive,destination,tool=map(lambda value:Path(value).absolute(),(client,archive,destination,tool))
    physical(client,True);physical(destination.parent,True)
    require(not destination.exists() and not destination.is_symlink(),'Extraction destination already exists')
    require(Path(descriptor['path']).resolve()==archive.resolve(),'Package descriptor path mismatch')
    options={key:descriptor[key] for key in ['appId','version','entrypoint']};options['archive']=descriptor
    inspect="const fs=require('fs'),path=require('path'),[client,file]=process.argv.slice(1),options=JSON.parse(fs.readFileSync(0,'utf8'));require(path.join(client,'directory-package.cjs')).inspect(file,options).then(value=>process.stdout.write(JSON.stringify(value))).catch(error=>{console.error(error);process.exitCode=1});"
    verify="const fs=require('fs'),path=require('path'),[client,root]=process.argv.slice(1),options=JSON.parse(fs.readFileSync(0,'utf8'));require(path.join(client,'directory-package.cjs')).verifyDirectory(root,options).catch(error=>{console.error(error);process.exitCode=1});"
    with held_read(archive) as archive_handle,held_read(tool) as tool_handle:
        require(held_digest(tool_handle)==tool_sha256,'Recorded native extractor changed')
        require(held_digest(archive_handle)==descriptor['sha256'],'Package hash changed')
        inventory=json.loads(node(client,inspect,options,archive))
        # The existing inspector checks every path/type/size/ratio and both full
        # archive hashes before the native tool receives the ZIP.
        physical(destination.parent,True);destination.mkdir(mode=0o700);owned=physical(destination,True)
        run=subprocess.run([str(tool),'x','-y','-bso0','-bsp0','-o'+str(destination),str(archive)],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        require(run.returncode==0,'Native extraction failed: '+run.stderr.decode('utf-8',errors='replace')[-2000:])
        after=physical(destination,True);require((owned.st_dev,owned.st_ino)==(after.st_dev,after.st_ino),'Extraction directory ownership changed')
        node(client,verify,{**options,'inventory':inventory},destination)
        after=physical(destination,True);require((owned.st_dev,owned.st_ino)==(after.st_dev,after.st_ino),'Verified directory ownership changed')
        require(held_digest(archive_handle)==descriptor['sha256'] and held_digest(tool_handle)==tool_sha256,'Held extraction inputs changed')
        return inventory


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['client','archive','destination','package-json','tool']: parser.add_argument('--'+key,required=True,type=Path)
    parser.add_argument('--tool-sha256',required=True)
    parser.add_argument('--expected-sha256',required=True,help='Package hash already authorized by the caller publisher-proof check')
    args=parser.parse_args()
    descriptor=json.loads(args.package_json.read_text(encoding='utf-8'))
    require(descriptor['sha256']==args.expected_sha256,'Package descriptor differs from caller-authorized hash')
    value=extract(args.client,args.archive,args.destination,descriptor,args.tool,args.tool_sha256)
    print(json.dumps(value,separators=(',',':')))


if __name__=='__main__': main()
