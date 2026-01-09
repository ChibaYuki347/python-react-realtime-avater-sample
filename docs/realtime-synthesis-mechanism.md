# リアルタイム音声合成の仕組み

本ドキュメントでは、Azure AI Speechサービスを利用したリアルタイム音声合成の仕組みについて説明します。特に、カスタムボイスとカスタムアバターを組み合わせたリアルタイム音声合成のプロセスに焦点を当てます。

## 事前準備

- Azure Subscription
- Foundry Resource
- AI Speechリソースの作成
- Speech Resource KeyとRegionの取得

## 環境のセットアップ

Speech SDKのインストールと設定を行います。以下のコマンドを使用して、必要なパッケージをインストールします。(Node.jsの場合)

```bash
npm install microsoft-cognitiveservices-speech-sdk
```

SDKを使う場合はコード内でimportします。

```javascript
import * as speechSdk from "microsoft-cognitiveservices-speech-sdk";
```

or

```javascript
const speechSdk = require("microsoft-cognitiveservices-speech-sdk");
```

プラットフォームはChrome, Microsoft Edgeを推奨。

## リアルタイム音声合成の流れ

1. バックエンドに向けてトークンリクエストを送信し、認証トークンを取得します。
2. 取得したトークンを使用してSpeech Configを作成します。
3. カスタムボイスとカスタムアバターの設定を行います。
4. リアルタイムアバターのコネクションを作成し、音声合成を行いアバターに喋らせる
5. コネクションを閉じる

### 1. トークンリクエスト送信について

[React sample](https://github.com/Azure-Samples/AzureSpeechReactSample)が参考になる。

getTokenOrRefreshToken関数を使用して、バックエンドからトークンを取得します。

例

```javascript
import axios from 'axios';
import Cookie from 'universal-cookie';

export async function getTokenOrRefresh() {
    const cookie = new Cookie();
    const speechToken = cookie.get('speech-token');

    if (speechToken === undefined) {
        try {
            const res = await axios.get('/api/get-speech-token');
            const token = res.data.token;
            const region = res.data.region;
            cookie.set('speech-token', region + ':' + token, {maxAge: 540, path: '/'});

            console.log('Token fetched from back-end: ' + token);
            return { authToken: token, region: region };
        } catch (err) {
            console.log(err.response.data);
            return { authToken: null, error: err.response.data };
        }
    } else {
        console.log('Token fetched from cookie: ' + speechToken);
        const idx = speechToken.indexOf(':');
        return { authToken: speechToken.slice(idx + 1), region: speechToken.slice(0, idx) };
    }
}
```

サーバー側では下記のような処理を行う。

```javascript
require('dotenv').config();
const express = require('express');
const axios = require('axios');
const bodyParser = require('body-parser');
const pino = require('express-pino-logger')();

const app = express();
app.use(bodyParser.urlencoded({ extended: false }));
app.use(pino);

app.get('/api/get-speech-token', async (req, res, next) => {
    res.setHeader('Content-Type', 'application/json');
    const speechKey = process.env.SPEECH_KEY;
    const speechRegion = process.env.SPEECH_REGION;

    if (speechKey === 'paste-your-speech-key-here' || speechRegion === 'paste-your-speech-region-here') {
        res.status(400).send('You forgot to add your speech key or region to the .env file.');
    } else {
        const headers = { 
            headers: {
                'Ocp-Apim-Subscription-Key': speechKey,
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        };

        try {
            const tokenResponse = await axios.post(`https://${speechRegion}.api.cognitive.microsoft.com/sts/v1.0/issueToken`, null, headers);
            res.send({ token: tokenResponse.data, region: speechRegion });
        } catch (err) {
            res.status(401).send('There was an error authorizing your speech key.');
        }
    }
});

app.listen(3001, () =>
    console.log('Express server is running on localhost:3001')
);
```

issueTokenエンドポイントにPOSTリクエストを送信し、認証トークンを取得します。

なお、`authorizationFromSubscriptionKey`メソッドはブラウザで使用すると認証キーが漏洩する可能性があるため、推奨されません。

### 2. Speech Configの作成

取得したトークンとリージョンを使用して、Speech Configを作成します。
言語とボイス名を設定します。

```javascript
const speechConfig = speechSdk.SpeechConfig.fromAuthorizationToken(authToken, region);
// Set either the `SpeechSynthesisVoiceName` or `SpeechSynthesisLanguage`.
speechConfig.speechSynthesisLanguage = "en-US";
speechConfig.speechSynthesisVoiceName = "en-US-AvaMultilingualNeural";   
```

Todo: ここでカスタムボイスが使えるかどうかは検証する。

### 3. カスタムボイスとカスタムアバターの設定

カスタムボイスについてはSpeech Configにカスタムボイス名を設定します。

カスタムアバターについて設定します。

```javascript
const avatarConfig = new SpeechSDK.AvatarConfig(
    "lisa", // Set avatar character here.
    "casual-sitting", // Set avatar style here.
);
```

Photo Avatarを使用する場合は、以下のように設定します。

```javascript
const avatarConfig = new SpeechSDK.AvatarConfig(
    "anika", // Set photo avatar character here.
);
avatarConfig.photoAvatarBaseModel = "vasa-1"; // Set photo avatar base model here.
```

### 4. リアルタイムアバターのコネクション作成と音声合成

Real-time AvaterはWebRTCプロトコルを使用する。
WebRTC Peer Connectionをセットアップします。

まず、WebRTCピア接続オブジェクトを作成します。WebRTCはピアツーピアであり、ネットワーク中継にはICEサーバーに依存します。SpeechサービスはICEサーバー情報を取得するためのREST APIを提供します。SpeechサービスからICEサーバーの詳細を取得することを推奨しますが、独自のサーバーを使用することも可能です。

Sample request to fetch ICE info:

```http
GET /cognitiveservices/avatar/relay/token/v1 HTTP/1.1

Host: westus2.tts.speech.microsoft.com
Ocp-Apim-Subscription-Key: YOUR_RESOURCE_KEY
```

前回の応答から取得したICEサーバーURL、ユーザー名、および認証情報を使用してWebRTCピア接続を作成します：

```javascript
// Create WebRTC peer connection
peerConnection = new RTCPeerConnection({
    iceServers: [{
        urls: [ "Your ICE server URL" ],
        username: "Your ICE server username",
        credential: "Your ICE server credential"
    }]
})
```

注意書き: ICEサーバーのURLは、turn（例：turn:relay.communication.microsoft.com:3478）またはstun（例：stun:relay.communication.microsoft.com:3478）で始まることができます。urlsには、turnのURLのみを含めてください。

次に、ピア接続のontrackコールバック内でビデオおよびオーディオプレイヤー要素を設定します。このコールバックは2回実行されます——ビデオ用とオーディオ用です。コールバック内で両方のプレイヤー要素を作成します：

```javascript
// Fetch WebRTC video/audio streams and mount them to HTML video/audio player elements
peerConnection.ontrack = function (event) {
    if (event.track.kind === 'video') {
        const videoElement = document.createElement(event.track.kind)
        videoElement.id = 'videoPlayer'
        videoElement.srcObject = event.streams[0]
        videoElement.autoplay = true
    }

    if (event.track.kind === 'audio') {
        const audioElement = document.createElement(event.track.kind)
        audioElement.id = 'audioPlayer'
        audioElement.srcObject = event.streams[0]
        audioElement.autoplay = true
    }
}

// Offer to receive one video track, and one audio track
peerConnection.addTransceiver('video', { direction: 'sendrecv' })
peerConnection.addTransceiver('audio', { direction: 'sendrecv' })
```

次に、Speech SDKを使用してアバター合成器を作成し、ピア接続でアバターサービスに接続します：

```javascript
// Create avatar synthesizer
var avatarSynthesizer = new SpeechSDK.AvatarSynthesizer(speechConfig, avatarConfig)

// Start avatar and establish WebRTC connection
avatarSynthesizer.startAvatarAsync(peerConnection).then(
    (r) => { console.log("Avatar started.") }
).catch(
    (error) => { console.log("Avatar failed to start. Error: " + error) }
);
```

リアルタイムAPIは、5分間アイドル状態が続いた場合、または接続開始から30分経過後に切断されます。アバターを長時間稼働させるには、自動再接続を有効にしてください。こちらの[JavaScriptサンプルコード（「自動再接続」で検索）](https://github.com/Azure-Samples/cognitive-services-speech-sdk/blob/master/samples/js/browser/avatar/README.md)を参照できる。

#### 音声合成の実行

設定後、アバター動画がブラウザで再生されます。アバターはまばたきし、わずかに動きますが、テキスト入力が送信されるまで話しません。

アバターに話させるには、アバター合成装置にテキストを送信してください：

```javascript
var spokenText = "I'm excited to try text to speech avatar."
avatarSynthesizer.speakTextAsync(spokenText).then(
    (result) => {
        if (result.reason === SpeechSDK.ResultReason.SynthesizingAudioCompleted) {
            console.log("Speech and avatar synthesized to video stream.")
        } else {
            console.log("Unable to speak. Result ID: " + result.resultId)
            if (result.reason === SpeechSDK.ResultReason.Canceled) {
                let cancellationDetails = SpeechSDK.CancellationDetails.fromResult(result)
                console.log(cancellationDetails.reason)
                if (cancellationDetails.reason === SpeechSDK.CancellationReason.Error) {
                    console.log(cancellationDetails.errorDetails)
                }
            }
        }
}).catch((error) => {
    console.log(error)
    avatarSynthesizer.close()
});
```

### 5. コネクションの終了

追加費用を避けるため、使用後は接続を閉じてください：

ブラウザを閉じると、WebRTCピア接続が解放され、数秒後にアバター接続も閉じられます。

アバターが5分間アイドル状態の場合、接続は自動的に閉じられます。

アバター接続は手動で閉じることができます：

```javascript
avatarSynthesizer.close()
```

## 参考資料

[How to use text to speech avatar with real-time synthesis](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/text-to-speech-avatar/real-time-synthesis-avatar)