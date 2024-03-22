const WebSocket = require("ws");
const express = require("express");
const { send } = require("process");
const app = express();
const server = require("http").createServer(app);
const wss = new WebSocket.Server({ server });

let socket = null;

const connectWebSocket = (url) => {
/*   if (socket) {
    socket.removeAllListeners();
  } */
  socket = new WebSocket(url);
  socket.on('open', () => console.log('Connected to Whisper'));
  socket.on('error', console.error);

  socket.on('close', () => {
    console.log('Disconnected from Whisper. Reconnecting...');
    // Try to reconnect after a delay
    setTimeout(() => connectWebSocket(url), 500);
  });
};
connectWebSocket('wss://d400-194-209-94-51.ngrok-free.app');

// Create WebSocket Connection

/* const transcriber = new WebSocket('wss://83a1-194-209-94-51.ngrok-free.app');

  transcriber.on('open', () => console.log('Connected to Whisper'));
  transcriber.on('error', console.error);
  transcriber.on('close', () => console.log('Disconnected from Whisper')); */


// Handle Web Socket Connection
wss.on('connection', async (ws) => {
  console.log('Twilio media stream WebSocket connected')
 
  

  ws.on('message', async (message) => {
    const msg = JSON.parse(message);
    switch (msg.event) {
      case 'connected':
        console.info('Twilio media stream connected');
        break;
      case 'start':
        console.info('Twilio media stream started');
        /* transcriber.send(msg, error => {
          if (error) console.error('Failed to send payload:', error);
        }); */
        break;
      case 'media':
        console.log(msg);
        socket.send(JSON.stringify(msg.media), error => { console.error('Failed to send payload:', error); });
        break;
      case 'stop':
        /* transcriber.send(msg.media.payload, error => { console.error('Failed to send payload:', error); }); */
        console.info('Twilio media stream stopped');
        socket.send("end_of_speech")
        break;
    }
  })
});

function sendToTranscriber(msg) {
  console.log(msg);
  return msg;
};

//Handle HTTP Request
app.get('/', (_, res) => res.type('text').send(sendToTranscriber().toString()));

app.post("/", async (req, res) => {
    res.type("text/xml")
    .send(
      `<Response>
        <Say language="de-DE">'Grüzi! '</Say>
        <Connect>
          <Stream url='wss://${req.headers.host}' />
          <Record /> 
        </Connect>
      </Response>
    `);
  });

console.log("Listening at Port 8080");
server.listen(8080);