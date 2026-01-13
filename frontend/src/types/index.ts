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
  customVoice: {
    enabled: boolean;
    name: string;
    deploymentId: string;
  };
  customAvatar: {
    enabled: boolean;
    character: string;
    style: string;
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
  customVoiceEnabled: boolean;
  customVoiceDeploymentId: string;
  customAvatarEnabled: boolean;
}