import axios, { AxiosResponse } from 'axios';
import Cookie from 'universal-cookie';
import { TokenResponse, ICEServerInfo, AppConfig } from '../types';

interface SpeechTokenResponse {
  token: string;
  region: string;
}

interface AzureICEServerResponse {
  // Azure Avatar API の実際の応答形式
  Urls?: string | string[];
  Username?: string;
  Password?: string;
  // 標準形式
  urls?: string | string[];
  username?: string;
  credential?: string;
  // 配列形式
  iceServers?: {
    urls: string | string[];
    username?: string;
    credential?: string;
  }[];
}

/**
 * アプリケーション設定を取得する関数
 */
export async function getAppConfig(): Promise<AppConfig> {
    try {
        const response = await axios.get<AppConfig>('/api/config');
        console.log('App config loaded:', response.data);
        return response.data;
    } catch (error) {
        console.error('Failed to load app config:', error);
        // フォールバック設定
        return {
            voice: {
                defaultName: 'ja-JP-NanamiNeural',
                defaultLanguage: 'ja-JP'
            },
            avatar: {
                defaultCharacter: 'lisa',
                defaultStyle: 'casual-sitting',
                defaultVideoFormat: 'mp4'
            },
            availableCustomVoices: [],
            customVoiceDeploymentIds: {},
            customAvatar: {
                enabled: false
            },
            region: 'southeastasia'
        };
    }
}

/**
 * Azure Speech Serviceのトークンを取得または更新する関数
 * ドキュメントのサンプルコードを基に実装
 */
export async function getTokenOrRefresh(): Promise<TokenResponse> {
    const cookie = new Cookie();
    const speechToken: string | undefined = cookie.get('speech-token');

    if (speechToken === undefined) {
        try {
            const res: AxiosResponse<SpeechTokenResponse> = await axios.get('/api/get-speech-token');
            const token: string = res.data.token;
            const region: string = res.data.region;
            cookie.set('speech-token', region + ':' + token, {maxAge: 540, path: '/'});

            console.log('Token fetched from back-end: ' + token);
            return { authToken: token, region: region };
        } catch (err: any) {
            console.log('Token取得エラー:', err.response?.data || err.message);
            return { authToken: null, error: err.response?.data || err.message };
        }
    } else {
        console.log('Token fetched from cookie: ' + speechToken);
        const idx: number = speechToken.indexOf(':');
        return { authToken: speechToken.slice(idx + 1), region: speechToken.slice(0, idx) };
    }
}

/**
 * Azure Avatar用のICEサーバー情報を取得する関数
 */
export async function getAvatarICEServerInfo(region: string, authToken: string): Promise<RTCIceServer[]> {
    try {
        console.log(`Fetching ICE server info for region: ${region}`);
        
        // Azure Avatar Service専用のICEサーバー情報取得
        const response = await axios.get<any>(
            `https://${region}.tts.speech.microsoft.com/cognitiveservices/avatar/relay/token/v1`,
            {
                headers: {
                    'Authorization': `Bearer ${authToken}`,
                    'Content-Type': 'application/json'
                }
            }
        );

        console.log('ICE server info received:', response.data);
        console.log('ICE server response type:', typeof response.data);
        console.log('ICE server response keys:', Object.keys(response.data || {}));
        
        // レスポンスの内容を詳細に確認
        if (!response.data) {
            throw new Error('Empty ICE server response');
        }
        
        // Azure Avatar APIの実際の応答形式に対応
        let iceServers: RTCIceServer[] = [];
        
        // Azure形式: {Urls: string[], Username: string, Password: string}
        if (response.data.Urls && response.data.Username && response.data.Password) {
            console.log('Azure Avatar ICE server format detected');
            
            // Azure TURNサーバー
            const azureServer: RTCIceServer = {
                urls: Array.isArray(response.data.Urls) ? response.data.Urls : [response.data.Urls],
                username: response.data.Username,
                credential: response.data.Password
            };
            
            // STUNサーバーも追加して接続成功率を向上
            const stunServers: RTCIceServer[] = [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ];
            
            console.log('Processed Azure TURN server:', azureServer);
            iceServers = [azureServer, ...stunServers];
        }
        // 標準形式: {urls, username, credential}
        else if (response.data.urls) {
            console.log('Standard ICE server format detected');
            const server: RTCIceServer = {
                urls: Array.isArray(response.data.urls) ? response.data.urls : [response.data.urls]
            };
            
            if (response.data.username) server.username = response.data.username;
            if (response.data.credential) server.credential = response.data.credential;
            
            console.log('Validated single server:', server);
            iceServers = [server];
        }
        // 配列形式: {iceServers: [...]}
        else if (response.data.iceServers && Array.isArray(response.data.iceServers)) {
            console.log('Array ICE server format detected');
            iceServers = response.data.iceServers.map((server: any, index: number) => {
                console.log(`Processing ICE server ${index}:`, server);
                
                if (!server.urls) {
                    console.error(`Server ${index} missing urls field:`, server);
                    return null;
                }
                
                const validServer: RTCIceServer = {
                    urls: Array.isArray(server.urls) ? server.urls : [server.urls]
                };
                
                if (server.username) validServer.username = server.username;
                if (server.credential) validServer.credential = server.credential;
                
                console.log(`Validated server ${index}:`, validServer);
                return validServer;
            }).filter((server: RTCIceServer | null) => server !== null);
        } else {
            console.error('Unknown ICE server response format:', response.data);
            throw new Error('Unknown Azure ICE server response format');
        }
        
        if (iceServers.length === 0) {
            throw new Error('No valid ICE servers found in response');
        }
        
        console.log('Final ICE servers array:', iceServers);
        return iceServers;
        
    } catch (error: any) {
        console.warn('Azure ICE server info取得に失敗しました:', error.message);
        
        // フォールバック: 複数のパブリックSTUN/TURNサーバーを使用
        return [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' },
            { urls: 'stun:stun2.l.google.com:19302' },
            { urls: 'stun:global.stun.twilio.com:3478' }
        ];
    }
}

/**
 * 旧バージョン用のICEサーバー情報取得関数（互換性維持）
 */
export async function getIceServerInfo(region: string, subscriptionKey: string): Promise<ICEServerInfo> {
    try {
        const response: AxiosResponse<ICEServerInfo> = await axios.get(
            `https://${region}.tts.speech.microsoft.com/cognitiveservices/avatar/relay/token/v1`,
            {
                headers: {
                    'Ocp-Apim-Subscription-Key': subscriptionKey
                }
            }
        );
        return response.data;
    } catch (error) {
        console.error('ICEサーバー情報の取得に失敗しました:', error);
        throw error;
    }
}