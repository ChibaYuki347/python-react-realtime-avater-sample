/**
 * Azure Speech-to-Text ユーティリティ（バックエンド経由）
 * AudioContext を使用して確実に WAV ファイルを生成
 */

export interface AudioRecorderConfig {
  sampleRate?: number;
  channelCount?: number;
  echoCancellation?: boolean;
  noiseSuppression?: boolean;
  autoGainControl?: boolean;
}

export interface SpeechToTextResult {
  success: boolean;
  text: string;
  error?: string;
}

/**
 * オーディオレコーダークラス（マイク入力を取得）
 * AudioContext を使用して確実に PCM/WAV を生成
 */
export class AudioRecorder {
  private audioContext: AudioContext | null = null;
  private mediaStreamAudioSourceNode: MediaStreamAudioSourceNode | null = null;
  private scriptProcessorNode: ScriptProcessorNode | null = null;
  private stream: MediaStream | null = null;
  private isRecording: boolean = false;
  private pcmChunks: Float32Array[] = [];
  private sampleRate: number = 16000;
  private isInitialized: boolean = false;

  /**
   * AudioContext を事前初期化（遅延を防ぐため）
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) {
      console.log('[AudioRecorder] Already initialized');
      return;
    }

    try {
      // AudioContext を事前に作成
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      this.sampleRate = this.audioContext.sampleRate;
      console.log('[AudioRecorder] Pre-initialized AudioContext, sampleRate:', this.sampleRate);

      // マイクへのアクセスを要求（パーミッションを取得）
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: { ideal: 16000 }
        }
      });

      console.log('[AudioRecorder] Microphone access granted');
      this.isInitialized = true;

      // ストリームはまだ使用しないので一旦停止
      this.stream.getTracks().forEach(track => track.enabled = false);
    } catch (error) {
      console.error('[AudioRecorder] 初期化エラー:', error);
      throw new Error('マイクの初期化に失敗しました');
    }
  }

  /**
   * 録音を開始
   */
  async start(): Promise<void> {
    try {
      // 初期化されていない場合は初期化
      if (!this.isInitialized) {
        await this.initialize();
      }

      // ストリームが停止している場合は再取得
      if (!this.stream || !this.stream.active) {
        this.stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
            sampleRate: { ideal: 16000 }
          }
        });
      } else {
        // 既存ストリームを有効化
        this.stream.getTracks().forEach(track => track.enabled = true);
      }

      // AudioContext が suspended の場合は resume
      if (this.audioContext!.state === 'suspended') {
        await this.audioContext!.resume();
      }

      // MediaStreamAudioSourceNode を作成
      this.mediaStreamAudioSourceNode = this.audioContext!.createMediaStreamSource(this.stream);

      // ScriptProcessorNode を作成（バッファサイズ: 4096）
      this.scriptProcessorNode = this.audioContext!.createScriptProcessor(4096, 1, 1);

      this.pcmChunks = [];
      this.isRecording = true;

      // オーディオデータを処理
      this.scriptProcessorNode.onaudioprocess = (event: AudioProcessingEvent) => {
        if (this.isRecording) {
          const inputData = event.inputBuffer.getChannelData(0);
          // Float32Array をコピーして保存
          this.pcmChunks.push(new Float32Array(inputData));
        }
      };

      // グラフに接続
      this.mediaStreamAudioSourceNode.connect(this.scriptProcessorNode);
      this.scriptProcessorNode.connect(this.audioContext!.destination);

      console.log('[AudioRecorder] 録音開始（即座）');
    } catch (error) {
      console.error('[AudioRecorder] マイクアクセスエラー:', error);
      throw new Error('マイクへのアクセスが拒否されました');
    }
  }

  /**
   * 録音を停止して WAV Blob を取得
   */
  async stop(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      if (!this.audioContext || !this.scriptProcessorNode) {
        reject(new Error('Recording not started'));
        return;
      }

      // グラフの接続を解除
      this.mediaStreamAudioSourceNode?.disconnect();
      this.scriptProcessorNode.disconnect();

      // ストリームを停止
      if (this.stream) {
        this.stream.getTracks().forEach(track => track.stop());
      }

      this.isRecording = false;

      console.log('[AudioRecorder] 録音完了:', this.pcmChunks.length, 'chunks');

      // PCM データを結合
      const totalLength = this.pcmChunks.reduce((acc, chunk) => acc + chunk.length, 0);
      const pcmData = new Float32Array(totalLength);
      let offset = 0;
      for (const chunk of this.pcmChunks) {
        pcmData.set(chunk, offset);
        offset += chunk.length;
      }

      console.log('[AudioRecorder] PCM data length:', pcmData.length, 'samples');
      console.log('[AudioRecorder] Duration:', (pcmData.length / this.sampleRate).toFixed(2), 'seconds');

      // PCM を 16-bit PCM に変換
      const pcm16 = new Int16Array(pcmData.length);
      for (let i = 0; i < pcmData.length; i++) {
        let sample = pcmData[i];
        sample = Math.max(-1, Math.min(1, sample)); // クリップ
        pcm16[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
      }

      // WAV ファイルを生成
      const wavBlob = this.encodeWAV(pcm16, this.sampleRate);

      console.log('[AudioRecorder] WAV Blob created:', wavBlob.size, 'bytes');
      console.log('[AudioRecorder] WAV MIME type:', wavBlob.type);

      this.pcmChunks = [];
      resolve(wavBlob);
    });
  }

  /**
   * PCM データを WAV フォーマットでエンコード
   */
  private encodeWAV(pcm16: Int16Array, sampleRate: number): Blob {
    const channels = 1;
    const bytesPerSample = 2; // 16-bit
    const dataLength = pcm16.length * bytesPerSample;

    // WAV ヘッダーを作成
    const wavHeader = new ArrayBuffer(44);
    const view = new DataView(wavHeader);

    let offset = 0;
    const writeString = (str: string) => {
      for (let i = 0; i < str.length; i++) {
        view.setUint8(offset++, str.charCodeAt(i));
      }
    };

    writeString('RIFF');
    view.setUint32(offset, 36 + dataLength, true); offset += 4;
    writeString('WAVE');
    writeString('fmt ');
    view.setUint32(offset, 16, true); offset += 4;
    view.setUint16(offset, 1, true); offset += 2;
    view.setUint16(offset, channels, true); offset += 2;
    view.setUint32(offset, sampleRate, true); offset += 4;
    view.setUint32(offset, sampleRate * channels * bytesPerSample, true); offset += 4;
    view.setUint16(offset, channels * bytesPerSample, true); offset += 2;
    view.setUint16(offset, 16, true); offset += 2;
    writeString('data');
    view.setUint32(offset, dataLength, true);

    // ヘッダーと PCM データを結合
    const wavData = new Uint8Array(44 + dataLength);
    wavData.set(new Uint8Array(wavHeader), 0);
    wavData.set(new Uint8Array(pcm16.buffer), 44);

    return new Blob([wavData], { type: 'audio/wav' });
  }

  /**
   * 録音をキャンセル
   */
  cancel(): void {
    if (this.isRecording) {
      this.mediaStreamAudioSourceNode?.disconnect();
      this.scriptProcessorNode?.disconnect();
    }

    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
    }

    this.pcmChunks = [];
    this.isRecording = false;
  }

  /**
   * 現在の録音状態を取得
   */
  getIsRecording(): boolean {
    return this.isRecording;
  }
}

/**
 * Azure Speech-to-Text クライアントクラス
 */
export class AzureSpeechToTextClient {
  private backendUrl: string;

  constructor(backendUrl: string = 'http://localhost:8000') {
    this.backendUrl = backendUrl;
  }

  /**
   * 音声ファイルを送信して認識
   */
  async transcribe(audioBlob: Blob): Promise<SpeechToTextResult> {
    try {
      console.log('[AzureSpeechToText] Starting transcription...');
      console.log('  Blob size:', audioBlob.size, 'bytes');
      console.log('  Blob type:', audioBlob.type);

      // FormData を使用してファイルを送信
      const formData = new FormData();
      formData.append('file', audioBlob, 'audio.wav');

      console.log('[AzureSpeechToText] Sending to:', `${this.backendUrl}/api/speech/transcribe`);

      const response = await fetch(`${this.backendUrl}/api/speech/transcribe`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
        console.error('[AzureSpeechToText] Server error:', response.status, errorData);
        return {
          success: false,
          text: '',
          error: errorData.detail || `HTTP ${response.status}`
        };
      }

      const result = await response.json();
      console.log('[AzureSpeechToText] 認識結果:', result);

      if (result.success) {
        return {
          success: true,
          text: result.text
        };
      } else {
        return {
          success: false,
          text: '',
          error: result.error || '音声認識に失敗しました'
        };
      }
    } catch (error) {
      console.error('[AzureSpeechToText] エラー:', error);
      return {
        success: false,
        text: '',
        error: `通信エラー: ${error instanceof Error ? error.message : '不明なエラー'}`
      };
    }
  }

  /**
   * ヘルスチェック
   */
  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${this.backendUrl}/api/speech/health`);
      return response.ok;
    } catch (error) {
      console.error('[AzureSpeechToText] ヘルスチェックエラー:', error);
      return false;
    }
  }
}

/**
 * Microphone Permission チェック
 */
export async function checkMicrophonePermission(): Promise<boolean> {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach(track => track.stop());
    return true;
  } catch (error) {
    console.error('[SpeechToText] マイクへのアクセスが拒否されました:', error);
    return false;
  }
}

/**
 * ブラウザがマイクをサポートしているか確認
 */
export function isBrowserSupported(): boolean {
  return !!(
    navigator.mediaDevices &&
    navigator.mediaDevices.getUserMedia
  );
}

/**
 * オーディオ環境の診断
 */
export async function checkAudioEnvironment(): Promise<{
  isSupported: boolean;
  hasMicrophonePermission: boolean;
  message: string;
}> {
  const isSupported = isBrowserSupported();
  let hasMicrophonePermission = false;

  if (isSupported) {
    hasMicrophonePermission = await checkMicrophonePermission();
  }

  const message = !isSupported
    ? 'お使いのブラウザはマイク入力をサポートしていません。'
    : !hasMicrophonePermission
    ? 'マイクへのアクセス権限がありません。ブラウザの設定を確認してください。'
    : 'マイク入力は利用可能です。';

  console.log('[AudioEnvironment]', {
    isSupported,
    hasMicrophonePermission,
    message
  });

  return {
    isSupported,
    hasMicrophonePermission,
    message
  };
}
