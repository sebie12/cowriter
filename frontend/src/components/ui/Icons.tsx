import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Icon({ size = 16, children, ...props }: IconProps) {
  return (
    <svg viewBox="0 0 16 16" width={size} height={size} fill="none" aria-hidden="true" {...props}>
      {children}
    </svg>
  );
}

export function PanelIcon(props: IconProps) {
  return <Icon {...props}><rect x="1.5" y="2" width="13" height="12" rx="2" stroke="currentColor" /><path d="M5.5 2v12" stroke="currentColor" /></Icon>;
}

export function NewChatIcon(props: IconProps) {
  return <Icon {...props}><path d="M3 2.5h7.5A2.5 2.5 0 0 1 13 5v4a2.5 2.5 0 0 1-2.5 2.5H7L3.5 14v-2.5H3A2 2 0 0 1 1 9.5v-5a2 2 0 0 1 2-2Z" stroke="currentColor" /><path d="M7 5v4M5 7h4" stroke="currentColor" strokeLinecap="round" /></Icon>;
}

export function SearchIcon(props: IconProps) {
  return <Icon {...props}><circle cx="7" cy="7" r="4.5" stroke="currentColor" /><path d="m10.5 10.5 3 3" stroke="currentColor" strokeLinecap="round" /></Icon>;
}

export function SettingsIcon(props: IconProps) {
  return <Icon {...props}><circle cx="8" cy="8" r="2.2" stroke="currentColor" /><path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M12.6 3.4l-1.4 1.4M4.8 11.2l-1.4 1.4" stroke="currentColor" strokeLinecap="round" /></Icon>;
}

export function DataIcon(props: IconProps) {
  return <Icon {...props}><ellipse cx="8" cy="3.5" rx="5.5" ry="2" stroke="currentColor" /><path d="M2.5 3.5v4c0 1.1 2.46 2 5.5 2s5.5-.9 5.5-2v-4M2.5 7.5v4c0 1.1 2.46 2 5.5 2s5.5-.9 5.5-2v-4" stroke="currentColor" /></Icon>;
}

export function ChevronDownIcon(props: IconProps) {
  return <Icon {...props}><path d="m4 6 4 4 4-4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /></Icon>;
}

export function ChevronRightIcon(props: IconProps) {
  return <Icon {...props}><path d="m6 4 4 4-4 4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /></Icon>;
}

export function CheckIcon(props: IconProps) {
  return <Icon {...props}><path d="m3 8.5 3 3 7-7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></Icon>;
}

export function CopyIcon(props: IconProps) {
  return <Icon {...props}><rect x="5" y="5" width="8" height="8" rx="1.5" stroke="currentColor" /><path d="M10.5 5V3.5A1.5 1.5 0 0 0 9 2H3.5A1.5 1.5 0 0 0 2 3.5V9A1.5 1.5 0 0 0 3.5 10.5H5" stroke="currentColor" /></Icon>;
}

export function CloseIcon(props: IconProps) {
  return <Icon {...props}><path d="m4 4 8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" /></Icon>;
}

export function RefreshIcon(props: IconProps) {
  return <Icon {...props}><path d="M13 5.5A5.5 5.5 0 1 0 13.2 10" stroke="currentColor" strokeLinecap="round" /><path d="M10.5 5.5H13V3" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" /></Icon>;
}

export function SendIcon(props: IconProps) {
  return <Icon {...props}><path d="M8 14V2M3.5 6.5 8 2l4.5 4.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></Icon>;
}
