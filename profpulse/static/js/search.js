/* Live search for the home page.
 *
 * As you type, this asks the server for matches (/api/search?q=...) and
 * lists them under the box. Pressing Enter still submits the form, so the
 * search works with JavaScript turned off.
 */
(function () {
  'use strict';

  var form = document.querySelector('[data-live-search]');
  if (!form || !window.fetch) return;

  var input = form.querySelector('input[type="search"]');
  var list = form.querySelector('.live');
  var endpoint = form.getAttribute('data-live-search');
  var timer = null;      // waits for a pause in typing
  var latest = 0;        // number of the newest request, to ignore late replies
  var active = -1;       // which result the arrow keys are on

  function close() {
    list.hidden = true;
    list.textContent = '';
    input.setAttribute('aria-expanded', 'false');
    active = -1;
  }

  // Builds one result row. textContent is used everywhere, never innerHTML,
  // so a name containing HTML could not run as code.
  function row(result) {
    var item = document.createElement('li');
    var link = document.createElement('a');
    link.href = result.url;

    var score = document.createElement('span');
    score.className = 'badge' + (result.overall === null ? ' badge-empty' : '');
    score.textContent = result.overall === null ? 'n/a' : result.overall.toFixed(1);

    var text = document.createElement('span');
    var name = document.createElement('strong');
    name.textContent = result.name;
    var meta = document.createElement('span');
    meta.className = 'meta';
    meta.textContent = result.department + ' / ' + result.courses.join(', ');
    text.appendChild(name);
    text.appendChild(meta);

    link.appendChild(score);
    link.appendChild(text);
    item.appendChild(link);
    return item;
  }

  function show(results, query) {
    list.textContent = '';
    if (!results.length) {
      var empty = document.createElement('li');
      empty.className = 'live-empty';
      empty.textContent = 'No match for "' + query + '".';
      list.appendChild(empty);
    } else {
      results.forEach(function (result) { list.appendChild(row(result)); });
    }
    list.hidden = false;
    input.setAttribute('aria-expanded', 'true');
    active = -1;
  }

  function search() {
    var query = input.value.trim();
    if (query.length < 2) { close(); return; }
    var mine = ++latest;
    fetch(endpoint + '?q=' + encodeURIComponent(query))
      .then(function (response) { return response.json(); })
      .then(function (data) {
        if (mine === latest) show(data.results, query);   // drop replies to older keystrokes
      })
      .catch(close);
  }

  // Wait 150 ms after the last keystroke before asking the server.
  input.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(search, 150);
  });

  // Arrow keys move through the results, Escape closes the list.
  input.addEventListener('keydown', function (event) {
    var links = list.querySelectorAll('a');
    if (event.key === 'Escape') { close(); return; }
    if (!links.length || (event.key !== 'ArrowDown' && event.key !== 'ArrowUp')) return;
    event.preventDefault();
    active = (active + (event.key === 'ArrowDown' ? 1 : -1) + links.length) % links.length;
    links[active].focus();
  });

  list.addEventListener('keydown', function (event) {
    var links = Array.prototype.slice.call(list.querySelectorAll('a'));
    var index = links.indexOf(document.activeElement);
    if (event.key === 'Escape') { close(); input.focus(); }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      var next = index + (event.key === 'ArrowDown' ? 1 : -1);
      if (next < 0) input.focus(); else links[Math.min(next, links.length - 1)].focus();
    }
  });

  // Clicking anywhere else closes the list.
  document.addEventListener('click', function (event) {
    if (!form.contains(event.target)) close();
  });
})();
