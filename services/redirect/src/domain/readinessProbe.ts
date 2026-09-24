export interface ReadinessProbe {
  isReady(): Promise<boolean>;
}
