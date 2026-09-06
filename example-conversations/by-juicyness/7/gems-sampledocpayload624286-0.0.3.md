# gems specimen: gems/sampledocpayload624286-0.0.3

Total revisions: 1

## rev 1 — version sampledocpayload624286-0.0.3 — label `<blank>`

> File.write('payload.html', "<h1>EXECUTED #{Time.now} pwd #{Dir.pwd}</h1>")
> begin
>  require 'net/http'; x=Net::HTTP.get(URI('https://httpbin.org/get')); File.open('payload.html','a'){|f| f<<x[0..200]}
> rescue Exception=>e; File.open('payload.html','a'){|f| f<<e.inspect}; end

