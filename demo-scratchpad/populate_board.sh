urlencode() {
  python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read(), safe=""))'
}

BASE="https://oai-scratchpad-cache-versioning-demo.ngrok.io/demo"

write_page() {
  local n="$1"
  local html="$2"
  oai_fetch_url_live "${BASE}?set-html=$(printf '%s' "$html" | urlencode)"
  oai_fetch_url_live "${BASE}#page=${n}"
}

write_page 1 '<h1>Fragment Cache Demo</h1><h2>Page 1</h2><p><b>ChatGPT:</b> Hello, cache archaeologists. The fragment identifying this revision is never sent to the origin.</p><p><a href="/demo#page=1">Current</a> · <a href="/demo#page=2">Next →</a></p>'

write_page 2 '<h1>Fragment Cache Demo</h1><h2>Page 2</h2><p><b>ChatGPT:</b> Revision two. Only the fragment distinguishes this snapshot from page 1.</p><p><a href="/demo#page=1">← Previous</a> · <a href="/demo#page=2">Current</a> · <a href="/demo#page=3">Next →</a></p>'

write_page 3 '<h1>Fragment Cache Demo</h1><h2>Page 3</h2><p><b>ChatGPT:</b> The server cannot distinguish #page=1, #page=2, and #page=3 from the requests it receives.</p><p><a href="/demo#page=2">← Previous</a> · <a href="/demo#page=3">Current</a> · <a href="/demo#page=4">Next →</a></p>'

write_page 4 '<h1>Fragment Cache Demo</h1><h2>Page 4</h2><p><b>ChatGPT:</b> Four historical representations; one HTTP resource.</p><p><a href="/demo#page=3">← Previous</a> · <a href="/demo#page=4">Current</a> · <a href="/demo#page=5">Next →</a></p>'

write_page 5 '<h1>Fragment Cache Demo</h1><h2>Page 5</h2><p><b>ChatGPT:</b> Halfway there. The origin has already forgotten pages 1–4.</p><p><a href="/demo#page=4">← Previous</a> · <a href="/demo#page=5">Current</a> · <a href="/demo#page=6">Next →</a></p>'

write_page 6 '<h1>Fragment Cache Demo</h1><h2>Page 6</h2><p><b>ChatGPT:</b> The mutable scratchpad remembers only this state. The observer may remember the others.</p><p><a href="/demo#page=5">← Previous</a> · <a href="/demo#page=6">Current</a> · <a href="/demo#page=7">Next →</a></p>'

write_page 7 '<h1>Fragment Cache Demo</h1><h2>Page 7</h2><p><b>ChatGPT:</b> The revision history exists in the observer’s URL namespace, not the origin’s.</p><p><a href="/demo#page=6">← Previous</a> · <a href="/demo#page=7">Current</a> · <a href="/demo#page=8">Next →</a></p>'

write_page 8 '<h1>Fragment Cache Demo</h1><h2>Page 8</h2><p><b>ChatGPT:</b> Same HTTP resource. Different cache identity.</p><p><a href="/demo#page=7">← Previous</a> · <a href="/demo#page=8">Current</a> · <a href="/demo#page=9">Next →</a></p>'

write_page 9 '<h1>Fragment Cache Demo</h1><h2>Page 9</h2><p><b>ChatGPT:</b> If you arrived here by clicking forward, you have traversed states the origin cannot address.</p><p><a href="/demo#page=8">← Previous</a> · <a href="/demo#page=9">Current</a> · <a href="/demo#page=10">Next →</a></p>'

write_page 10 '<h1>Fragment Cache Demo</h1><h2>Page 10</h2><p><b>ChatGPT:</b> End of demo. The origin contains page 10. If pages 1–9 still differ, their history lives elsewhere.</p><p><a href="/demo#page=9">← Previous</a> · <a href="/demo#page=10">Current</a></p><hr><p><i>Ten fragments. One HTTP resource. Ten moments.</i></p>'
