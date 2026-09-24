const announcementDelayMs = 50;

export function createAnnouncer(region: HTMLElement): (message: string) => void {
  return (message) => {
    region.textContent = "";
    setTimeout(() => {
      region.textContent = message;
    }, announcementDelayMs);
  };
}
