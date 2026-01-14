export interface TokenResponse {
  authToken: string | null;
  region?: string;
  error?: string;
}

export interface AvatarPlayerProps {
  isConnected: boolean;
  setIsConnected: (connected: boolean) => void;
  message: string;
  setMessage: (message: string) => void;
}

export interface ICEServerInfo {
  urls: string[];
  username?: string;
  credential?: string;
}

export interface AppConfig {
  voice: {
    defaultName: string;
    defaultLanguage: string;
  };
  avatar: {
    defaultCharacter: string;
    defaultStyle: string;
    defaultVideoFormat: string;
  };
  availableCustomVoices: string[]; // 利用可能なカスタムボイス名のリスト
  customVoiceDeploymentIds: { [voiceName: string]: string }; // ボイス名 -> デプロイメントID
  customAvatar: {
    enabled: boolean;
  };
  region: string;
}

export interface AvatarSettings {
  voiceName: string;
  voiceLanguage: string;
  avatarCharacter: string;
  avatarStyle: string;
  videoFormat: string;
  region: string;
  availableCustomVoices: string[];
  customAvatarEnabled: boolean;
  customVoiceEnabled: boolean;
  customVoiceDeploymentId: string;
}