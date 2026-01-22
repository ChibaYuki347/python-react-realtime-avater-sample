/**
 * Azure Speech-to-Text ユーティリティ（バックエンド経由）
 * バックエンドの Azure Speech Service を使用してネットワークエラーを回避
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
 */
export class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private stream: MediaStream | null = null;
  private isRecording: boolean = false;

  /**
   * 録音を開始
   */
  async start(): Promise<void> {
    try {
      // マイクへのアクセスを要求
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      // MediaRecorder を作成
      this.mediaRecorder = new MediaRecorder(this.stream);
      this.audioChunks = [];
      this.isRecording = true;

      // audio/wav フォーマットでデータを収集
      this.mediaRecorder.ondataavailable = (event) => {
        this.audioChunks.push(event.data);
      };

      // 録音開始
      this.mediaRecorder.start();
      console.log('[AudioRecorder] 録音開始');
    } catch (error) {
      console.error('[AudioRecorder] マイクアクセスエラー:', error);
      throw new Error('マイクへのアクセスが拒否されました');
    }
  }

  /**
   * 録音を停止して Blob を取得
   */
  async stop(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder) {
        reject(new Error('Recording not started'));
        return;
      }

      this.mediaRecorder.onstop = () => {
        // ストリームを停止
        if (this.stream) {
          this.stream.getTracks().forEach(track => track.stop());
        }

        // Blob を作成
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
        this.audioChunks = [];
        this.isRecording = false;

        console.log('[AudioRecorder] 録音完了:', audioBlob.size, 'bytes');
        resolve(audioBlob);
      };

      this.mediaRecorder.stop();
    });
  }

  /**
   * 録音をキャンセル
   */
  cancel(): void {
    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop();
    }

    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
    }

    this.audioChunks = [];
    this.isRecording = false;
    console.log('[AudioRecorder] 録音キャンセル');
  }

  /**
   * 録音中かどうか
   */
  getIsRecording(): boolean {
    return this.isRecording;
  }
}

/**
 * Azure Speech-to-Text クライアント（バックエンド経由）
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
      // FormData を使用してファイルを送信
      const formData = new FormData();
      formData.append('file', audioBlob, 'audio.wav');

      const response = await fetch(`${this.backendUrl}/api/speech/transcribe`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
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
    // ストリームを停止
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
