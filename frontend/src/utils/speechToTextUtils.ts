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
  private retryCount: number = 0;
  private maxRetries: number = 3;

  constructor() {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn('Web Speech API is not supported in this browser');
      return;
    }
    
    this.recognition = new SpeechRecognition();
    this.setupRecognition();
  }

  /**
   * エラーコードを人間が読める形に変換
   */
  private getErrorMessage(error: string): string {
    const errorMap: { [key: string]: string } = {
      'no-speech': '音声が検出されませんでした。マイクが正しく接続されているか確認してください。',
      'audio-capture': 'マイクが見つかりません。マイク接続を確認してください。',
      'not-allowed': 'マイクへのアクセスが拒否されました。ブラウザの設定を確認してください。',
      'network': 'ネットワーク接続エラー。インターネット接続を確認してください。',
      'aborted': '音声認識がキャンセルされました。',
      'service-not-available': '音声認識サービスが利用できません。',
      'bad-grammar': '音声認識文法エラーが発生しました。',
      'unknown': '不明なエラーが発生しました。'
    };
    return errorMap[error] || errorMap['unknown'];
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
      const errorMessage = this.getErrorMessage(event.error);
      console.error('[Speech-to-Text] エラー:', event.error, ' - ', errorMessage);
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
   * エラーメッセージを取得
   */
  public getErrorMessage(error: string): string {
    const errorMap: { [key: string]: string } = {
      'no-speech': '音声が検出されませんでした。マイクが正しく接続されているか確認してください。',
      'audio-capture': 'マイクが見つかりません。マイク接続を確認してください。',
      'not-allowed': 'マイクへのアクセスが拒否されました。ブラウザの設定を確認してください。',
      'network': 'ネットワーク接続エラー。インターネット接続を確認してください。',
      'aborted': '音声認識がキャンセルされました。',
      'service-not-available': '音声認識サービスが利用できません。',
      'bad-grammar': '音声認識文法エラーが発生しました。',
      'unknown': '不明なエラーが発生しました。'
    };
    return errorMap[error] || errorMap['unknown'];
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

/**
 * Speech-to-Text の環境情報をチェック
 */
export function checkSpeechToTextEnvironment(): {
  isSupported: boolean;
  isSecure: boolean;
  environment: string;
  message: string;
} {
  const isSupported = isBrowserSupported();
  const isSecure = window.location.protocol === 'https:' || window.location.hostname === 'localhost';
  
  let message = '';
  if (!isSupported) {
    message = 'お使いのブラウザは Web Speech API に対応していません。Chrome、Edge、Safari で試してください。';
  } else if (!isSecure) {
    message = 'Web Speech API は HTTPS または localhost でのみ動作します。';
  } else {
    message = 'Speech-to-Text は利用可能です。';
  }

  console.log('[Speech-to-Text]', {
    isSupported,
    isSecure,
    protocol: window.location.protocol,
    hostname: window.location.hostname,
    message
  });

  return {
    isSupported,
    isSecure,
    environment: `${window.location.protocol}//${window.location.hostname}`,
    message
  };
}
