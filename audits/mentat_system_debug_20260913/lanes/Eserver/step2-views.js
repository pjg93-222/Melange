/* Step 2 (lane E-server): saved Chart Studio views in server.py.

   Console.list_views/get_view/save_view/delete_view over
   <data root>\studio\views\<32hex>.json (read_json + atomic_json under
   Console.lock), the GET and POST routes, the read-only refusal, and the
   512 KB payload ceiling measured on the request body rather than on the
   parsed object (the body is what the socket and the disk have to carry).

   get_view returns None for an unknown id instead of raising, because do_GET
   catches only ValueError/OSError/KeyError/BadZipFile: a RunNotFound raised
   from a GET route would escape the handler, not become a 404.

   Usage: node apply-e.js step2-views.js [--check] */
'use strict';

const CONSOLE_METHODS = `    # Chart Studio saved views. They live under the data root beside the runs,
    # so a second console opened on the same data root lists the same views;
    # that is what "save here, open on the mirror console" means. A read-only
    # preview refuses the writes at the route, before the body is parsed.

    def studio_directory(self, *parts):
        return self.root.joinpath('studio', *parts)

    def list_views(self):
        """Saved views for the picker, newest first, without their sheets."""
        directory = self.studio_directory('views')
        values = []
        if directory.is_dir():
            for path in directory.glob('*.json'):
                value = read_json(path)
                if value.get('id') != path.stem or not isinstance(value.get('sheets'), list):
                    continue
                values.append({'id': value['id'], 'name': value.get('name', ''),
                               'saved_at': value.get('saved_at', 0),
                               'sourceKey': value.get('sourceKey', ''),
                               'source': value.get('source', {}),
                               'sheet_count': len(value['sheets'])})
        values.sort(key=lambda item: (-(item['saved_at'] or 0), item['id']))
        return {'views': values}

    def get_view(self, identifier):
        """One saved view with its sheets, or None when this console has no such view."""
        if not re.fullmatch(r'[a-f0-9]{32}', identifier or ''):
            raise ValueError('That is not a saved view identifier.')
        value = read_json(self.studio_directory('views', identifier + '.json'))
        if value.get('id') != identifier or not isinstance(value.get('sheets'), list):
            return None
        return {'id': value['id'], 'name': value.get('name', ''), 'saved_at': value.get('saved_at', 0),
                'sourceKey': value.get('sourceKey', ''), 'source': value.get('source', {}),
                'sheets': value['sheets'], 'active': value.get('active', 0)}

    def save_view(self, data):
        name = str(data.get('name', '')).strip()
        if not 1 <= len(name) <= 80:
            raise ValueError('Name the view: between 1 and 80 characters.')
        source_key, source = data.get('sourceKey'), data.get('source')
        if not isinstance(source_key, str) or not isinstance(source, dict):
            raise ValueError('A saved view carries the source it was built from.')
        sheets = data.get('sheets')
        if not isinstance(sheets, list) or not 1 <= len(sheets) <= 24:
            raise ValueError('Save between 1 and 24 sheets in one view.')
        if any(not isinstance(sheet, dict) or not str(sheet.get('name', '')).strip() for sheet in sheets):
            raise ValueError('Every sheet in a saved view needs a name.')
        active = data.get('active')
        if not isinstance(active, int) or isinstance(active, bool):
            raise ValueError('The active sheet is a sheet number.')
        identifier = uuid.uuid4().hex
        value = {'id': identifier, 'name': name, 'saved_at': time.time(), 'sourceKey': source_key,
                 'source': source, 'sheets': sheets, 'active': active}
        directory = self.studio_directory('views')
        with self.lock:
            directory.mkdir(parents=True, exist_ok=True)
            atomic_json(directory / (identifier + '.json'), value)
        return {'id': identifier, 'saved_at': value['saved_at']}

    def delete_view(self, data):
        """Remove a saved view. Deleting one that is already gone is success."""
        identifier = str(data.get('id', ''))
        if not re.fullmatch(r'[a-f0-9]{32}', identifier):
            raise ValueError('That is not a saved view identifier.')
        with self.lock:
            try:
                (self.studio_directory('views') / (identifier + '.json')).unlink()
            except FileNotFoundError:
                pass
        return {'deleted': True}

`;

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  files: [{
    path: 'server.py',
    edits: [
      // 1. Console methods, ahead of the run listing.
      {find: '    def runs(self):\n        values = []\n',
       replace: CONSOLE_METHODS + '    def runs(self):\n        values = []\n'},

      // 2. GET routes, ahead of the static asset table.
      {find: '            assets = STATIC_ASSETS\n',
       replace:
        "            if parsed.path == '/api/studio/views':\n" +
        "                identifier = query.get('id', [''])[0]\n" +
        "                if not identifier:\n" +
        "                    return self.send(app.list_views())\n" +
        "                view = app.get_view(identifier)\n" +
        "                if view is None:\n" +
        "                    return self.send({'error': 'That saved view is not on this console.'}, 404)\n" +
        "                return self.send({'view': view})\n" +
        '            assets = STATIC_ASSETS\n'},

      // 3. Read-only refusal, ahead of the generic one so the message names
      //    the surface the writer was using.
      {find: "        analytical_paths = {'/api/contributions/query', '/api/contributions/records', '/api/contributions/geography'}\n",
       replace:
        "        analytical_paths = {'/api/contributions/query', '/api/contributions/records', '/api/contributions/geography'}\n" +
        "        if getattr(self.server.app, 'read_only', False) and self.path.startswith('/api/studio/views'):\n" +
        '            self.discard_body()\n' +
        '            return self.send({\'error\': \'Saved views are read-only in this preview console; save from the original console.\'}, 403)\n'},

      // 4. Payload ceiling for a saved view, measured on the request body.
      {find: '            length = int(self.headers.get("Content-Length", "0"))\n' +
             '            if length < 1 or length > 7_000_000:\n' +
             '                self.discard_body()\n' +
             '                raise ValueError("Request is empty or too large.")\n',
       replace: '            length = int(self.headers.get("Content-Length", "0"))\n' +
             '            if length < 1 or length > 7_000_000:\n' +
             '                self.discard_body()\n' +
             '                raise ValueError("Request is empty or too large.")\n' +
             "            if self.path == '/api/studio/views' and length > 512 * 1024:\n" +
             '                self.discard_body()\n' +
             "                raise ValueError('That view is too large to save. Remove a sheet and save again.')\n"},

      // 5. POST routes.
      {find: '            if self.path == "/api/workers":\n' +
             '                return self.send(self.server.app.set_workers(data))\n',
       replace: '            if self.path == "/api/workers":\n' +
             '                return self.send(self.server.app.set_workers(data))\n' +
             "            if self.path == '/api/studio/views':\n" +
             '                return self.send(self.server.app.save_view(data))\n' +
             "            if self.path == '/api/studio/views/delete':\n" +
             '                return self.send(self.server.app.delete_view(data))\n'}
    ]
  }]
};
