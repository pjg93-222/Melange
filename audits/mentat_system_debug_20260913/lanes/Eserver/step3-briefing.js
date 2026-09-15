/* Step 3 (lane E-server): the briefing tray in server.py.

   Store: <data root>\studio\briefing\index.json (the ordered item list) and one
   <id>.svg per item. The SVG is written first and the index second, so an
   interrupted add leaves an unreferenced file rather than an item whose chart
   is missing; both writes go through a temporary plus os.replace.

   The SVG is served as text/plain, never image/svg+xml: an SVG document served
   from this origin as an image type is script-capable, and this one is built
   from report text. text/plain plus the existing nosniff header is not.

   A full tray is a 409, which needs an exception class the handler can map;
   ValueError is already spoken for by 400. Conflict is added beside RunNotFound.

   Usage: node apply-e.js step3-briefing.js [--check] */
'use strict';

const METHODS = `    # The briefing tray: one shared tray per data root (Paul's v1 ruling), so
    # every console on this data root shows the same items in the same order.

    def briefing(self):
        """The ordered tray. Missing or damaged index files read as empty."""
        value = read_json(self.studio_directory('briefing', 'index.json'))
        items = value.get('items')
        return {'items': [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []}

    def briefing_item(self, identifier):
        """The stored SVG for one item, or None when this console has no such item."""
        if not re.fullmatch(r'[a-f0-9]{32}', identifier or ''):
            raise ValueError('That is not a briefing item identifier.')
        if not any(item.get('id') == identifier for item in self.briefing()['items']):
            return None
        try:
            return self.studio_directory('briefing', identifier + '.svg').read_text(encoding='utf-8')
        except OSError:
            return None

    def add_to_briefing(self, data):
        svg = data.get('svg')
        if not isinstance(svg, str) or not svg.startswith('<svg'):
            raise ValueError('A briefing item carries the chart it was made from.')
        if len(svg.encode('utf-8')) > 6 * 1024 * 1024:
            raise ValueError('Narrow the view before adding it: this chart is over 6 MB.')

        def dimension(value):
            try:
                return max(0, int(round(float(value))))
            except (TypeError, ValueError):
                return 0

        identifier = uuid.uuid4().hex
        item = {'id': identifier, 'title': str(data.get('title', '')).strip(),
                'scope': str(data.get('scope', '')).strip(), 'note': str(data.get('note', '')).strip(),
                'basis': str(data.get('basis', '')).strip(), 'sheetId': str(data.get('sheetId', '')).strip(),
                'sheetName': str(data.get('sheetName', '')).strip(),
                'source': data.get('source') if isinstance(data.get('source'), dict) else {},
                'provenance': data.get('provenance') if isinstance(data.get('provenance'), dict) else {},
                'width': dimension(data.get('width')), 'height': dimension(data.get('height')),
                'added_at': time.time(), 'origin': str(data.get('origin', '')).strip()}
        directory = self.studio_directory('briefing')
        with self.lock:
            directory.mkdir(parents=True, exist_ok=True)
            items = self.briefing()['items']
            if len(items) >= 40:
                raise Conflict('The briefing holds 40 items. Remove one before adding another.')
            temporary = directory / (identifier + '.svg.' + uuid.uuid4().hex + '.tmp')
            temporary.write_text(svg, encoding='utf-8')
            os.replace(temporary, directory / (identifier + '.svg'))
            items.append(item)
            atomic_json(directory / 'index.json', {'items': items})
        return {'id': identifier, 'added_at': item['added_at']}

    def remove_from_briefing(self, data):
        """Remove one item. Removing one that is already gone is success."""
        identifier = str(data.get('id', ''))
        if not re.fullmatch(r'[a-f0-9]{32}', identifier):
            raise ValueError('That is not a briefing item identifier.')
        directory = self.studio_directory('briefing')
        with self.lock:
            directory.mkdir(parents=True, exist_ok=True)
            items = [item for item in self.briefing()['items'] if item.get('id') != identifier]
            atomic_json(directory / 'index.json', {'items': items})
            try:
                (directory / (identifier + '.svg')).unlink()
            except FileNotFoundError:
                pass
        return {'removed': True}

    def order_briefing(self, data):
        """Reorder the tray. The list has to be a permutation of what is there."""
        ids = data.get('ids')
        if not isinstance(ids, list) or any(not isinstance(value, str) for value in ids):
            raise ValueError('Send the briefing order as a list of item identifiers.')
        directory = self.studio_directory('briefing')
        with self.lock:
            directory.mkdir(parents=True, exist_ok=True)
            items = self.briefing()['items']
            index = {item.get('id'): item for item in items}
            if len(ids) != len(items) or len(set(ids)) != len(ids) or any(value not in index for value in ids):
                raise ValueError('The briefing order must list every item in the tray exactly once.')
            atomic_json(directory / 'index.json', {'items': [index[value] for value in ids]})
        return {'ok': True}

`;

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  files: [{
    path: 'server.py',
    edits: [
      // 1. A conflict is not a bad request: the caller is right, the tray is full.
      {find: 'class RunNotFound(Exception):\n',
       replace: 'class Conflict(Exception):\n' +
                '    """A well-formed request the current state cannot accept yet."""\n\n\n' +
                'class RunNotFound(Exception):\n'},

      // 2. Console methods, ahead of the run listing (after the saved views).
      {find: '    def runs(self):\n        values = []\n',
       replace: METHODS + '    def runs(self):\n        values = []\n'},

      // 3. GET routes, beside the saved-view route.
      {find: "            if parsed.path == '/api/studio/views':\n",
       replace:
        "            if parsed.path == '/api/studio/briefing':\n" +
        '                return self.send(app.briefing())\n' +
        "            if parsed.path == '/api/studio/briefing/item':\n" +
        "                svg = app.briefing_item(query.get('id', [''])[0])\n" +
        '                if svg is None:\n' +
        "                    return self.send({'error': 'That briefing item is not on this console.'}, 404)\n" +
        "                return self.send(svg.encode('utf-8'), content_type='text/plain; charset=utf-8')\n" +
        "            if parsed.path == '/api/studio/views':\n"},

      // 4. Read-only refusal for the tray, beside the saved-view refusal.
      {find: "        if getattr(self.server.app, 'read_only', False) and self.path.startswith('/api/studio/views'):\n",
       replace:
        "        if getattr(self.server.app, 'read_only', False) and self.path.startswith('/api/studio/briefing'):\n" +
        '            self.discard_body()\n' +
        "            return self.send({'error': 'The briefing is read-only in this preview console.'}, 403)\n" +
        "        if getattr(self.server.app, 'read_only', False) and self.path.startswith('/api/studio/views'):\n"},

      // 5. POST routes.
      {find: "            if self.path == '/api/studio/views':\n" +
             '                return self.send(self.server.app.save_view(data))\n',
       replace:
        "            if self.path == '/api/studio/briefing/add':\n" +
        '                return self.send(self.server.app.add_to_briefing(data))\n' +
        "            if self.path == '/api/studio/briefing/remove':\n" +
        '                return self.send(self.server.app.remove_from_briefing(data))\n' +
        "            if self.path == '/api/studio/briefing/order':\n" +
        '                return self.send(self.server.app.order_briefing(data))\n' +
        "            if self.path == '/api/studio/views':\n" +
        '                return self.send(self.server.app.save_view(data))\n'},

      // 6. Map Conflict to 409 ahead of the 404 and 400 handlers.
      {find: '        except RunNotFound as error:\n' +
             '            return self.send({"error": str(error)}, 404)\n',
       replace: '        except Conflict as error:\n' +
             "            return self.send({'error': str(error)}, 409)\n" +
             '        except RunNotFound as error:\n' +
             '            return self.send({"error": str(error)}, 404)\n'}
    ]
  }]
};
