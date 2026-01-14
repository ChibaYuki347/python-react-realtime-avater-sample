import React, { useState, useRef, useEffect } from 'react';
import * as speechSdk from 'microsoft-cognitiveservices-speech-sdk';
import { getTokenOrRefresh, getAvatarICEServerInfo, getAppConfig } from '../utils/speechUtils';
import { AvatarPlayerProps, AvatarSettings, AppConfig } from '../types';

const AvatarPlayer: React.FC<AvatarPlayerProps> = ({ 
  isConnected, 
  setIsConnected, 
  message, 
  setMessage 
}) => {
    const [status, setStatus] = useState<string>('準備中');
    const [error, setError] = useState<string | null>(null);
    const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
    const [debugInfo, setDebugInfo] = useState<string[]>([]);
    const [connectionRetries, setConnectionRetries] = useState<number>(0);
    const [appConfig, setAppConfig] = useState<AppConfig | null>(null);
    const [avatarSettings, setAvatarSettings] = useState<AvatarSettings>({
        voiceName: 'ja-JP-NanamiNeural',
        voiceLanguage: 'ja-JP',
        avatarCharacter: 'lisa',
        avatarStyle: 'casual-sitting',
        videoFormat: 'mp4',
        region: 'eastus',
        availableCustomVoices: [],
        customAvatarEnabled: false,
        customVoiceEnabled: false,
        customVoiceDeploymentId: ''
    });
    
    // refs with proper typing
    const videoRef = useRef<HTMLVideoElement>(null);
    const audioRef = useRef<HTMLAudioElement>(null);
    const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
    const avatarSynthesizerRef = useRef<speechSdk.AvatarSynthesizer | null>(null);
    const speechConfigRef = useRef<speechSdk.SpeechConfig | null>(null);

    // デバッグ情報を追加する関数
    const addDebugInfo = (info: string) => {
        const timestamp = new Date().toLocaleTimeString();
        const debugMessage = `[${timestamp}] ${info}`;
        console.log(debugMessage);
        setDebugInfo(prev => [...prev.slice(-9), debugMessage]); // 最新10件を保持
    };

    useEffect(() => {
        // アプリケーション設定を読み込み
        const loadConfig = async () => {
            try {
                const config = await getAppConfig();
                setAppConfig(config); // 設定を保存
                
                // デフォルトボイスまたはカスタムボイスを選択
                const selectedVoiceName = config.voice.defaultName;
                
                // カスタムボイスかどうかを判定し、デプロイメントIDを取得
                const isCustomVoice = config.availableCustomVoices?.includes(selectedVoiceName) || false;
                const deploymentId = isCustomVoice ? config.customVoiceDeploymentIds?.[selectedVoiceName] || '' : '';
                
                setAvatarSettings({
                    voiceName: selectedVoiceName,
                    voiceLanguage: config.voice.defaultLanguage,
                    avatarCharacter: config.avatar.defaultCharacter,
                    avatarStyle: config.avatar.defaultStyle,
                    videoFormat: config.avatar.defaultVideoFormat,
                    region: config.region,
                    availableCustomVoices: config.availableCustomVoices || [],
                    customAvatarEnabled: config.customAvatar?.enabled || false,
                    customVoiceEnabled: isCustomVoice,
                    customVoiceDeploymentId: deploymentId
                });
                addDebugInfo(`設定読み込み完了: voice=${selectedVoiceName}, isCustomVoice=${isCustomVoice}, deploymentId=${deploymentId}, avatar=${config.avatar.defaultCharacter}`);
            } catch (error) {
                console.error('設定読み込み失敗:', error);
                addDebugInfo(`設定読み込み失敗: ${error}`);
            }
        };
        
        loadConfig();
        
        // コンポーネントのアンマウント時にクリーンアップ
        return () => {
            addDebugInfo("コンポーネントクリーンアップ開始");
            if (avatarSynthesizerRef.current) {
                avatarSynthesizerRef.current.close();
            }
            if (peerConnectionRef.current) {
                peerConnectionRef.current.close();
            }
        };
    }, []);

    /**
     * メディアストリームの詳細情報を取得
     */
    const getStreamInfo = (stream: MediaStream): string => {
        const videoTracks = stream.getVideoTracks();
        const audioTracks = stream.getAudioTracks();
        return `Video tracks: ${videoTracks.length} (enabled: ${videoTracks.filter(t => t.enabled).length}), Audio tracks: ${audioTracks.length} (enabled: ${audioTracks.filter(t => t.enabled).length})`;
    };

    /**
     * WebRTC接続の再試行機能
     */
    const retryConnection = async (authToken: string, region: string): Promise<void> => {
        const maxRetries = 3;
        
        if (connectionRetries >= maxRetries) {
            throw new Error(`接続試行回数が上限(${maxRetries}回)に達しました`);
        }

        addDebugInfo(`接続再試行 ${connectionRetries + 1}/${maxRetries}`);
        setConnectionRetries(prev => prev + 1);
        
        // 少し待機してから再試行
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        return initializeAvatarInternal(authToken, region, true);
    };

    /**
     * アバター接続の内部実装
     */
    const initializeAvatarInternal = async (authToken: string, region: string, isRetry: boolean = false): Promise<void> => {
        if (!isRetry) {
            setConnectionRetries(0);
        }

        setStatus('Speech Configを設定中...');
        
        // Speech Configを作成
        const speechConfig = speechSdk.SpeechConfig.fromAuthorizationToken(authToken, region);
        speechConfig.speechSynthesisLanguage = avatarSettings.voiceLanguage;
        speechConfig.speechSynthesisVoiceName = avatarSettings.voiceName;
        
        // カスタムボイス使用時の設定
        if (avatarSettings.customVoiceEnabled && avatarSettings.customVoiceDeploymentId) {
            // エンドポイントIDを設定
            (speechConfig as any).endpointId = avatarSettings.customVoiceDeploymentId;
            addDebugInfo(`カスタムボイスエンドポイントID設定: ${avatarSettings.customVoiceDeploymentId}`);
        }
        
        speechConfigRef.current = speechConfig;
        addDebugInfo(`Speech Config作成完了: lang=${speechConfig.speechSynthesisLanguage}, voice=${speechConfig.speechSynthesisVoiceName}, customVoice=${avatarSettings.customVoiceEnabled}`);

        setStatus('アバター設定中...');
        
        // アバター設定を作成
        const avatarConfig = new speechSdk.AvatarConfig(
            avatarSettings.avatarCharacter, // アバターキャラクター
            avatarSettings.avatarStyle, // アバタースタイル
            avatarSettings.videoFormat as any // ビデオフォーマット（型定義の問題を回避）
        );
        
        // カスタムアバターの場合はcustomizedをtrueに設定
        if (avatarSettings.customAvatarEnabled) {
            (avatarConfig as any).customized = true;
            
            // カスタムアバター使用時、カスタムボイスを使う場合はuseBuiltInVoiceをfalseに設定
            if (avatarSettings.customVoiceEnabled) {
                (avatarConfig as any).useBuiltInVoice = false;
                addDebugInfo(`useBuiltInVoice設定: false（カスタムボイス使用）`);
            } else {
                (avatarConfig as any).useBuiltInVoice = true;
                addDebugInfo(`useBuiltInVoice設定: true（Voice Sync for Avatar使用）`);
            }
        }
        
        addDebugInfo(`アバター設定作成完了: character=${avatarSettings.avatarCharacter}, style=${avatarSettings.avatarStyle}, customized=${avatarSettings.customAvatarEnabled}`);

        setStatus('ICEサーバー情報取得中...');
        
        // Azure専用のICEサーバー情報を取得
        let iceServers: RTCIceServer[];
        try {
            iceServers = await getAvatarICEServerInfo(region, authToken);
            addDebugInfo(`Azure ICEサーバー情報取得成功: ${iceServers.length}個のサーバー`);
            console.log('ICE servers for RTCPeerConnection:', iceServers);
            
            // 各サーバーの詳細をログ出力
            iceServers.forEach((server, index) => {
                console.log(`ICE Server ${index}:`, server);
                addDebugInfo(`Server ${index}: urls=${Array.isArray(server.urls) ? server.urls.join(',') : server.urls}, username=${server.username || 'なし'}`);
            });
        } catch (error) {
            addDebugInfo(`Azure ICEサーバー取得失敗、フォールバック使用: ${error}`);
            iceServers = [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ];
        }

        setStatus('WebRTC接続を作成中...');
        
        // WebRTCピア接続を作成
        let peerConnection: RTCPeerConnection;
        try {
            const config: RTCConfiguration = {
                iceServers: iceServers,
                iceTransportPolicy: 'all',
                bundlePolicy: 'balanced',
                iceCandidatePoolSize: 10, // ICE候補プールサイズを増やして接続成功率向上
                rtcpMuxPolicy: 'require'   // RTCP多重化を必須にしてパフォーマンス向上
            };
            
            console.log('Creating RTCPeerConnection with config:', config);
            addDebugInfo(`RTCPeerConnection設定: ${JSON.stringify(config, null, 2)}`);
            
            peerConnection = new RTCPeerConnection(config);
            peerConnectionRef.current = peerConnection;
            addDebugInfo("WebRTC PeerConnection作成完了");
        } catch (peerError) {
            console.error('RTCPeerConnection作成エラー:', peerError);
            addDebugInfo(`RTCPeerConnection作成失敗: ${peerError}`);
            
            // フォールバック: 基本的なSTUNサーバーで再試行
            addDebugInfo("基本STUNサーバーで再試行中...");
            const fallbackConfig: RTCConfiguration = {
                iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
                iceTransportPolicy: 'all',
                bundlePolicy: 'balanced'
            };
            
            peerConnection = new RTCPeerConnection(fallbackConfig);
            peerConnectionRef.current = peerConnection;
            addDebugInfo("WebRTC PeerConnection (フォールバック) 作成完了");
        }

        // ICE接続状態の監視とリスタート機能
        let iceRestartTimer: NodeJS.Timeout;
        
        peerConnection.oniceconnectionstatechange = () => {
            addDebugInfo(`ICE接続状態: ${peerConnection.iceConnectionState}`);
            
            if (peerConnection.iceConnectionState === 'disconnected') {
                addDebugInfo("ICE接続が切断されました。リスタートを試行します...");
                
                // 10秒後にICEリスタートを実行
                iceRestartTimer = setTimeout(async () => {
                    try {
                        addDebugInfo("ICE接続をリスタートしています...");
                        
                        // ICEリスタートのためのoffer/answer交換
                        const offer = await peerConnection.createOffer({ iceRestart: true });
                        await peerConnection.setLocalDescription(offer);
                        
                        // アバターシンセサイザーに新しいofferを送信
                        if (avatarSynthesizerRef.current) {
                            await avatarSynthesizerRef.current.startAvatarAsync(peerConnection);
                            addDebugInfo("ICEリスタート完了");
                        }
                    } catch (error) {
                        addDebugInfo(`ICEリスタート失敗: ${error}`);
                        console.error('ICE restart failed:', error);
                    }
                }, 10000);
            }
            
            if (peerConnection.iceConnectionState === 'connected' || 
                peerConnection.iceConnectionState === 'completed') {
                addDebugInfo("ICE接続が復旧しました");
                if (iceRestartTimer) {
                    clearTimeout(iceRestartTimer);
                }
            }
            
            // 接続失敗時の再試行ロジック
            if (peerConnection.iceConnectionState === 'failed' && !isRetry) {
                addDebugInfo("ICE接続失敗、再試行を開始");
                if (iceRestartTimer) {
                    clearTimeout(iceRestartTimer);
                }
                
                setTimeout(() => {
                    retryConnection(authToken, region).catch(error => {
                        addDebugInfo(`再試行も失敗: ${error.message}`);
                        setError(error.message);
                        setIsConnected(false);
                    });
                }, 1000);
            }
        };

        // 接続状態の監視と詳細診断
        peerConnection.onconnectionstatechange = () => {
            addDebugInfo(`接続状態: ${peerConnection.connectionState}`);
            
            if (peerConnection.connectionState === 'connected') {
                addDebugInfo("WebRTC接続が確立されました");
                setConnectionRetries(0); // 成功時はリセット
            } else if (peerConnection.connectionState === 'failed') {
                addDebugInfo("WebRTC接続が完全に失敗しました");
                
                // 接続失敗時の診断情報を収集
                const stats = {
                    iceConnectionState: peerConnection.iceConnectionState,
                    connectionState: peerConnection.connectionState,
                    signalingState: peerConnection.signalingState,
                    iceGatheringState: peerConnection.iceGatheringState
                };
                
                addDebugInfo(`診断情報: ${JSON.stringify(stats)}`);
                console.error('WebRTC connection failed with stats:', stats);
            }
        };

        // ICE候補の詳細監視
        peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                const candidate = event.candidate;
                addDebugInfo(`ICE候補: ${candidate.type} ${candidate.protocol} ${candidate.address || 'hidden'} priority=${candidate.priority}`);
            } else {
                addDebugInfo("ICE候補収集完了");
            }
        };
        
        // ICE収集状態の監視
        peerConnection.onicegatheringstatechange = () => {
            addDebugInfo(`ICE収集状態: ${peerConnection.iceGatheringState}`);
        };

        // ontrackコールバックを設定
        peerConnection.ontrack = (event: RTCTrackEvent) => {
            addDebugInfo(`Track受信: ${event.track.kind}, readyState: ${event.track.readyState}`);
            const stream = event.streams[0];
            addDebugInfo(`Stream情報: ${getStreamInfo(stream)}`);

            if (event.track.kind === 'video') {
                if (videoRef.current) {
                    videoRef.current.srcObject = stream;
                    videoRef.current.autoplay = true;
                    videoRef.current.muted = true; // autoplayのため
                    videoRef.current.playsInline = true;
                    
                    // ビデオの読み込み状態を監視
                    videoRef.current.onloadedmetadata = () => {
                        addDebugInfo(`ビデオメタデータ読み込み完了: ${videoRef.current?.videoWidth}x${videoRef.current?.videoHeight}`);
                    };
                    
                    videoRef.current.oncanplay = () => {
                        addDebugInfo("ビデオ再生可能");
                    };
                    
                    videoRef.current.onplay = () => {
                        addDebugInfo("ビデオ再生開始");
                    };
                    
                    videoRef.current.onerror = (e) => {
                        addDebugInfo(`ビデオエラー: ${e}`);
                    };

                    // 手動で再生を試行
                    setTimeout(() => {
                        if (videoRef.current) {
                            videoRef.current.play().then(() => {
                                addDebugInfo("ビデオ手動再生成功");
                            }).catch((e) => {
                                addDebugInfo(`ビデオ手動再生失敗: ${e.message}`);
                            });
                        }
                    }, 1000);
                }
            }
            
            if (event.track.kind === 'audio') {
                if (audioRef.current) {
                    audioRef.current.srcObject = stream;
                    audioRef.current.autoplay = true;
                    
                    // オーディオの状態を監視
                    audioRef.current.oncanplay = () => {
                        addDebugInfo("オーディオ再生可能");
                    };
                    
                    audioRef.current.onplay = () => {
                        addDebugInfo("オーディオ再生開始");
                    };
                    
                    audioRef.current.onerror = (e) => {
                        addDebugInfo(`オーディオエラー: ${e}`);
                    };

                    // 手動で再生を試行
                    setTimeout(() => {
                        if (audioRef.current) {
                            audioRef.current.play().then(() => {
                                addDebugInfo("オーディオ手動再生成功");
                            }).catch((e) => {
                                addDebugInfo(`オーディオ手動再生失敗: ${e.message}`);
                            });
                        }
                    }, 1000);
                }
            }
        };

        // トランシーバーを追加
        peerConnection.addTransceiver('video', { direction: 'sendrecv' });
        peerConnection.addTransceiver('audio', { direction: 'sendrecv' });
        addDebugInfo("トランシーバー追加完了");

        setStatus('アバターシンセサイザーを作成中...');
        
        // アバターシンセサイザーを作成
        const avatarSynthesizer = new speechSdk.AvatarSynthesizer(speechConfig, avatarConfig);
        
        avatarSynthesizerRef.current = avatarSynthesizer;
        addDebugInfo("AvatarSynthesizer作成完了");

        setStatus('アバターに接続中...');
        
        // アバターを開始
        await avatarSynthesizer.startAvatarAsync(peerConnection);
        addDebugInfo("Avatar接続完了");
        
        setStatus('接続完了');
        setIsConnected(true);
    };

    /**
     * アバター接続を初期化する関数
     */
    const initializeAvatar = async (): Promise<void> => {
        try {
            setError(null);
            setDebugInfo([]);
            setStatus('トークンを取得中...');
            addDebugInfo("アバター初期化開始");
            
            // トークンを取得
            const { authToken, region, error: tokenError } = await getTokenOrRefresh();
            if (tokenError || !authToken || !region) {
                throw new Error(`トークン取得エラー: ${tokenError}`);
            }
            addDebugInfo(`トークン取得成功: region=${region}`);

            await initializeAvatarInternal(authToken, region);
        } catch (error) {
            console.error('アバター初期化エラー:', error);
            const errorMessage = error instanceof Error ? error.message : String(error);
            setError(errorMessage);
            addDebugInfo(`初期化エラー: ${errorMessage}`);
            setStatus('接続エラー');
            setIsConnected(false);
        }
    };
    /**
     * 音声合成とアバター表示を実行する関数
     */
    const speakText = async (): Promise<void> => {
        if (!message.trim()) {
            setError('メッセージを入力してください');
            return;
        }

        if (!isConnected || !avatarSynthesizerRef.current) {
            setError('アバターに接続されていません');
            return;
        }

        try {
            setIsSpeaking(true);
            setError(null);
            addDebugInfo(`音声合成開始: "${message}"`);
            
            // SSML形式で音声合成を実行
            const ssml = `
            <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='${avatarSettings.voiceLanguage}'>
                <voice name='${avatarSettings.voiceName}'>
                    ${message}
                </voice>
            </speak>`;

            // 音声合成を実行
            avatarSynthesizerRef.current.speakSsmlAsync(ssml);
            addDebugInfo("音声合成リクエスト送信完了");

        } catch (error) {
            console.error('音声合成エラー:', error);
            const errorMessage = error instanceof Error ? error.message : String(error);
            setError(errorMessage);
            addDebugInfo(`音声合成エラー: ${errorMessage}`);
        } finally {
            setIsSpeaking(false);
        }
    };

    /**
     * アバター接続を切断する関数
     */
    const disconnectAvatar = (): void => {
        addDebugInfo("切断処理開始");
        
        if (avatarSynthesizerRef.current) {
            avatarSynthesizerRef.current.close();
            avatarSynthesizerRef.current = null;
            addDebugInfo("AvatarSynthesizer切断完了");
        }

        if (peerConnectionRef.current) {
            peerConnectionRef.current.close();
            peerConnectionRef.current = null;
            addDebugInfo("PeerConnection切断完了");
        }

        // メディア要素のsrcObjectをクリア
        if (videoRef.current) {
            videoRef.current.srcObject = null;
        }
        if (audioRef.current) {
            audioRef.current.srcObject = null;
        }

        setIsConnected(false);
        setStatus('切断しました');
        setConnectionRetries(0);
        addDebugInfo("切断処理完了");
    };

    /**
     * デバッグ情報をクリアする関数
     */
    const clearDebugInfo = (): void => {
        setDebugInfo([]);
        setError(null);
    };

    return (
        <div className="avatar-player-container">
            
            {/* Settings Panel */}
            <div className="settings-panel" style={{
                backgroundColor: '#f5f5f5',
                padding: '20px',
                marginBottom: '20px',
                borderRadius: '8px',
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                gap: '15px'
            }}>
                <h3 style={{gridColumn: '1 / -1', margin: '0 0 15px 0'}}>設定</h3>
                
                <div>
                    <label style={{display: 'block', marginBottom: '5px', fontWeight: 'bold'}}>音声名:</label>
                    <input
                        type="text"
                        value={avatarSettings.voiceName}
                        onChange={(e) => setAvatarSettings(prev => ({...prev, voiceName: e.target.value}))}
                        placeholder="ja-JP-NanamiNeural"
                        style={{width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc'}}
                    />
                </div>
                
                <div>
                    <label style={{display: 'block', marginBottom: '5px', fontWeight: 'bold'}}>音声言語:</label>
                    <input
                        type="text"
                        value={avatarSettings.voiceLanguage}
                        onChange={(e) => setAvatarSettings(prev => ({...prev, voiceLanguage: e.target.value}))}
                        placeholder="ja-JP"
                        style={{width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc'}}
                    />
                </div>
                
                <div>
                    <label style={{display: 'block', marginBottom: '5px', fontWeight: 'bold'}}>アバターキャラクター:</label>
                    <input
                        type="text"
                        value={avatarSettings.avatarCharacter}
                        onChange={(e) => setAvatarSettings(prev => ({...prev, avatarCharacter: e.target.value}))}
                        placeholder="lisa"
                        style={{width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc'}}
                    />
                </div>
                
                <div>
                    <label style={{display: 'block', marginBottom: '5px', fontWeight: 'bold'}}>アバタースタイル:</label>
                    <input
                        type="text"
                        value={avatarSettings.avatarStyle}
                        onChange={(e) => setAvatarSettings(prev => ({...prev, avatarStyle: e.target.value}))}
                        placeholder="casual-sitting"
                        style={{width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc'}}
                    />
                </div>
                
                <div>
                    <label style={{display: 'block', marginBottom: '5px', fontWeight: 'bold'}}>ビデオフォーマット:</label>
                    <select
                        value={avatarSettings.videoFormat}
                        onChange={(e) => setAvatarSettings(prev => ({...prev, videoFormat: e.target.value}))}
                        style={{width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc'}}
                    >
                        <option value="mp4">MP4</option>
                        <option value="webm">WebM</option>
                    </select>
                </div>
                
                <div>
                    <label style={{display: 'block', marginBottom: '5px', fontWeight: 'bold'}}>リージョン:</label>
                    <input
                        type="text"
                        value={avatarSettings.region}
                        onChange={(e) => setAvatarSettings(prev => ({...prev, region: e.target.value}))}
                        placeholder="eastus"
                        style={{width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc'}}
                    />
                </div>
                
                {/* カスタムボイス設定 */}
                <div style={{gridColumn: '1 / -1', borderTop: '1px solid #ddd', paddingTop: '15px', marginTop: '10px'}}>
                    <h4 style={{margin: '0 0 10px 0', fontWeight: 'bold'}}>利用可能なボイス</h4>
                    {avatarSettings.availableCustomVoices.length > 0 ? (
                        <div>
                            <label style={{display: 'block', marginBottom: '5px'}}>利用可能なボイス:</label>
                            <div style={{backgroundColor: '#f8f9fa', padding: '10px', borderRadius: '4px', border: '1px solid #dee2e6'}}>
                                {avatarSettings.availableCustomVoices.map((voiceName) => (
                                    <div key={voiceName} style={{
                                        display: 'flex', 
                                        justifyContent: 'space-between', 
                                        alignItems: 'center',
                                        marginBottom: '5px',
                                        padding: '5px',
                                        backgroundColor: voiceName === avatarSettings.voiceName ? '#e3f2fd' : 'transparent',
                                        borderRadius: '3px'
                                    }}>
                                        <span><strong>{voiceName}</strong></span>
                                        <button
                                            onClick={() => {
                                                const isCustomVoice = avatarSettings.availableCustomVoices.includes(voiceName);
                                                const deploymentId = isCustomVoice ? (appConfig?.customVoiceDeploymentIds?.[voiceName] || '') : '';
                                                setAvatarSettings(prev => ({
                                                    ...prev, 
                                                    voiceName,
                                                    customVoiceEnabled: isCustomVoice,
                                                    customVoiceDeploymentId: deploymentId
                                                }));
                                            }}
                                            style={{
                                                padding: '2px 8px',
                                                fontSize: '12px',
                                                backgroundColor: voiceName === avatarSettings.voiceName ? '#1976d2' : '#6c757d',
                                                color: 'white',
                                                border: 'none',
                                                borderRadius: '3px',
                                                cursor: 'pointer'
                                            }}
                                        >
                                            {voiceName === avatarSettings.voiceName ? '選択中' : '選択'}
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div style={{color: '#6c757d', fontStyle: 'italic'}}>
                            利用可能なボイスが設定されていません。環境変数 AVAILABLE_CUSTOM_VOICES で設定してください。<br/>
                            <strong>例:</strong> CUSTOM_VOICES={`{"MyVoice1": "deployment-id-1", "MyVoice2": "deployment-id-2"}`}
                        </div>
                    )}
                </div>
                
                {/* カスタムアバター設定 */}
                <div style={{gridColumn: '1 / -1', borderTop: '1px solid #ddd', paddingTop: '15px', marginTop: '10px'}}>
                    <label style={{display: 'flex', alignItems: 'center', fontWeight: 'bold', marginBottom: '10px'}}>
                        <input
                            type="checkbox"
                            checked={avatarSettings.customAvatarEnabled}
                            onChange={(e) => setAvatarSettings(prev => ({...prev, customAvatarEnabled: e.target.checked}))}
                            style={{marginRight: '8px'}}
                        />
                        カスタムアバター使用
                    </label>
                    {avatarSettings.customAvatarEnabled && (
                        <div style={{marginLeft: '20px', color: '#666', fontSize: '14px'}}>
                            <p>※ カスタムアバターを使用する場合、アバターキャラクターにカスタムアバター名を入力してください</p>
                            <p>※ 例: "YourCustomAvatarName"</p>
                        </div>
                    )}
                </div>
            </div>

            {/* メイン表示エリア */}
            <div className="avatar-display">
                <video 
                    ref={videoRef}
                    className="avatar-video"
                    controls={false}
                    autoPlay
                    playsInline
                    muted
                    style={{
                        width: '100%',
                        maxWidth: '640px',
                        height: '360px',
                        backgroundColor: '#000',
                        border: '1px solid #ccc',
                        borderRadius: '8px'
                    }}
                />
                <audio 
                    ref={audioRef}
                    autoPlay
                    style={{ display: 'none' }}
                />
            </div>

            {/* 状態表示エリア */}
            <div className="status-section">
                <h3>状態: {status}</h3>
                <p>接続状況: {isConnected ? '✅ 接続済み' : '❌ 未接続'}</p>
                {connectionRetries > 0 && (
                    <p>再試行回数: {connectionRetries}/3</p>
                )}
                
                {error && (
                    <div className="error-message" style={{ 
                        backgroundColor: '#ffebee', 
                        color: '#c62828', 
                        padding: '10px', 
                        borderRadius: '4px', 
                        margin: '10px 0' 
                    }}>
                        エラー: {error}
                    </div>
                )}
            </div>

            {/* 操作ボタンエリア */}
            <div className="control-section" style={{ margin: '20px 0' }}>
                {!isConnected ? (
                    <button 
                        onClick={initializeAvatar}
                        style={{
                            backgroundColor: '#4CAF50',
                            color: 'white',
                            padding: '10px 20px',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '16px'
                        }}
                    >
                        アバターに接続
                    </button>
                ) : (
                    <div>
                        <div style={{ margin: '10px 0' }}>
                            <textarea
                                value={message}
                                onChange={(e) => setMessage(e.target.value)}
                                placeholder="話させたいメッセージを入力してください"
                                style={{
                                    width: '100%',
                                    maxWidth: '600px',
                                    height: '80px',
                                    padding: '10px',
                                    border: '1px solid #ccc',
                                    borderRadius: '4px',
                                    fontSize: '14px',
                                    resize: 'vertical'
                                }}
                            />
                        </div>
                        
                        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                            <button 
                                onClick={speakText}
                                disabled={isSpeaking || !message.trim()}
                                style={{
                                    backgroundColor: isSpeaking ? '#ccc' : '#2196F3',
                                    color: 'white',
                                    padding: '10px 20px',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: isSpeaking ? 'not-allowed' : 'pointer',
                                    fontSize: '16px'
                                }}
                            >
                                {isSpeaking ? '話しています...' : 'アバターに話させる'}
                            </button>
                            
                            <button 
                                onClick={disconnectAvatar}
                                style={{
                                    backgroundColor: '#f44336',
                                    color: 'white',
                                    padding: '10px 20px',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '16px'
                                }}
                            >
                                接続を切断
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* デバッグ情報エリア */}
            <div className="debug-section" style={{ 
                marginTop: '20px', 
                padding: '15px', 
                backgroundColor: '#f5f5f5', 
                borderRadius: '8px',
                fontSize: '12px',
                fontFamily: 'monospace'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <h4 style={{ margin: '0' }}>デバッグ情報</h4>
                    <button 
                        onClick={clearDebugInfo}
                        style={{
                            backgroundColor: '#9e9e9e',
                            color: 'white',
                            padding: '5px 10px',
                            border: 'none',
                            borderRadius: '3px',
                            cursor: 'pointer',
                            fontSize: '12px'
                        }}
                    >
                        クリア
                    </button>
                </div>
                
                <div style={{ 
                    maxHeight: '200px', 
                    overflowY: 'auto', 
                    backgroundColor: 'white', 
                    padding: '10px', 
                    borderRadius: '4px',
                    border: '1px solid #ddd'
                }}>
                    {debugInfo.length === 0 ? (
                        <p style={{ color: '#666', margin: '0' }}>デバッグ情報はここに表示されます</p>
                    ) : (
                        debugInfo.map((info, index) => (
                            <div key={index} style={{ margin: '2px 0', lineHeight: '1.4' }}>
                                {info}
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
};

export default AvatarPlayer;