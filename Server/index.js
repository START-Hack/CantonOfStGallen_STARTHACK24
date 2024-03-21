const http = require('http');
const WebSocket = require("ws");
const VoiceResponse = require('twilio').twiml.VoiceResponse;

http
  .createServer((req, res) => {
    // Create TwiML response
    const response = new VoiceResponse();
    const connect = response.connect();

    response.say({
      voice: 'Google.de-DE-Standard-A',
      language: 'de-DE'
  }, 'Grüzi! Sie haben die Kanton St. Gallen Hotline erreicht. Wie kann ich Ihnen helfen?');

    response.record({ transcribe: true, maxLength: 30 });

    // End the call with <Hangup>
    response.hangup();
  
    res.writeHead(200, { 'Content-Type': 'text/xml' });
    console.log(response.toString());
    res.end(response.toString());
  })
  .listen(1337, '127.0.0.1');
console.log('TwiML server running at http://127.0.0.1:1337/');
