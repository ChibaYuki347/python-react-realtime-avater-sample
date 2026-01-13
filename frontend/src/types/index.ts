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