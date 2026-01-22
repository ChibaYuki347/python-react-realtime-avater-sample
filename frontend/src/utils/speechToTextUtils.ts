/**
 * Azure Speech-to-Text ユーティリティ
 * Web Speech API と Azure Speech SDK を使用した音声入力
 */

export interface SpeechToTextConfig {
  speechToken: string;
  speechRegion: string;
  language: string;
}

export interface SpeechRecognitionResult {
  text: string;
  isFinal: boolean;
  confidence?: number;
}

/**
 * Web Speech API を使用した簡易的なリアルタイム音声認識
 */
export class WebSpeechRecognizer {
  private recognition: any;
  private isListening: boolean = false;
  private interimTranscript: string = '';

  constructor() {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn('Web Speech API is not supported in this browser');
      return;
    }
    
    this.recognition = new SpeechRecognition();
    this.setupRecognition();
  }

  private setupRecognition() {
    if (!this.recognition) return;

    // 言語設定
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.language = 'ja-JP';

    // 認識開始時
    this.recognition.onstart = () => {
      console.log('[Speech-to-Text] 音声認識開始');
      this.isListening = true;
      this.interimTranscript = '';
    };

    // 認識中（中間結果）
    this.recognition.onresult = (event: any) => {
      this.interimTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;

        if (event.results[i].isFinal) {
          console.log('[Speech-to-Text] 最終結果:', transcript);
        } else {
          this.interimTranscript += transcript;
          console.log('[Speech-to-Text] 中間結果:', this.interimTranscript);
        }
      }
    };

    // エラーハンドリング
    this.recognition.onerror = (event: any) => {
      console.error('[Speech-to-Text] エラー:', event.error);
    };

    // 認識終了時
    this.recognition.onend = () => {
      console.log('[Speech-to-Text] 音声認識終了');
      this.isListening = false;
    };
  }

  /**
   * 音声認識を開始
   */
  public start(): void {
    if (!this.recognition) {
      console.error('Web Speech API is not supported');
      return;
    }

    try {
      this.recognition.start();
    } catch (error) {
      console.error('[Speech-to-Text] 音声認識開始エラー:', error);
    }
  }

  /**
   * 音声認識を停止
   */
  public stop(): Promise<string> {
    return new Promise((resolve, reject) => {
      if (!this.recognition) {
        reject(new Error('Web Speech API is not supported'));
        return;
      }

      const finalText = this.interimTranscript;
      
      try {
        this.recognition.stop();
        // 少し遅延して、onendイベント処理を待つ
        setTimeout(() => {
          resolve(finalText);
        }, 100);
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * 現在の中間テキストを取得
   */
  public getInterimTranscript(): string {
    return this.interimTranscript;
  }

  /**
   * リスニング状態を取得
   */
  public getIsListening(): boolean {
    return this.isListening;
  }

  /**
   * キャンセル
   */
  public abort(): void {
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch (error) {
        console.error('[Speech-to-Text] キャンセルエラー:', error);
      }
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
    console.error('[Speech-to-Text] マイクへのアクセスが拒否されました:', error);
    return false;
  }
}

/**
 * ブラウザの Web Speech API をサポートしているか確認
 */
export function isBrowserSupported(): boolean {
  const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  return !!SpeechRecognition;
}
