// Replace the user's home directory prefix with "~" so the username isn't shown.
const HOME_PREFIX = /^(?:\/home\/[^/]+|\/Users\/[^/]+|\/root(?=\/|$)|[A-Za-z]:[\\/]Users[\\/][^\\/]+)/;

export function displayPath(path: string): string {
  return path.replace(HOME_PREFIX, "~");
}
