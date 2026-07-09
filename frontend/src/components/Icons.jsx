const base = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

const Icon = ({ children, size = 17 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
    {children}
  </svg>
);

export const IconDashboard = (p) => (
  <Icon {...p}><rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" /><rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" /></Icon>
);

export const IconQueue = (p) => (
  <Icon {...p}><path d="M4 6h16M4 12h16M4 18h10" /><circle cx="19" cy="18" r="2.4" /></Icon>
);

export const IconSearch = (p) => (
  <Icon {...p}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></Icon>
);

export const IconWaitlist = (p) => (
  <Icon {...p}><path d="M8 7a4 4 0 1 0 8 0 4 4 0 0 0-8 0Z" /><path d="M4 21v-1a6 6 0 0 1 6-6h1" /><path d="M17 14v7M13.5 17.5H20.5" /></Icon>
);

export const IconCalendar = (p) => (
  <Icon {...p}><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M8 3v4M16 3v4M3 10h18" /></Icon>
);

export const IconBuilding = (p) => (
  <Icon {...p}><rect x="4" y="3" width="16" height="18" rx="1.5" /><path d="M9 21v-4h6v4M8 7h2M8 11h2M14 7h2M14 11h2" /></Icon>
);

export const IconTasks = (p) => (
  <Icon {...p}><path d="m4 6 2 2 3.5-3.5" /><path d="m4 14 2 2 3.5-3.5" /><path d="M12 7h9M12 15h9" /></Icon>
);

export const IconBell = (p) => (
  <Icon {...p}><path d="M6 9a6 6 0 1 1 12 0c0 5 2 6 2 6H4s2-1 2-6" /><path d="M10.3 20a2 2 0 0 0 3.4 0" /></Icon>
);

export const IconPhone = (p) => (
  <Icon {...p}><path d="M5 4h4l1.7 4.3-2.2 1.6a12.5 12.5 0 0 0 5.6 5.6l1.6-2.2L20 15v4a2 2 0 0 1-2.2 2A16.5 16.5 0 0 1 3 6.2 2 2 0 0 1 5 4Z" /></Icon>
);

export const IconAlert = (p) => (
  <Icon {...p}><path d="M12 3 2.5 20h19L12 3Z" /><path d="M12 10v4M12 17.2v.3" /></Icon>
);

export const IconArrowRight = (p) => (
  <Icon {...p}><path d="M4 12h16M14 6l6 6-6 6" /></Icon>
);

export const IconCheck = (p) => (
  <Icon {...p}><path d="m4.5 12.5 5 5 10-11" /></Icon>
);

export const IconClock = (p) => (
  <Icon {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3.5 2" /></Icon>
);

export const IconUser = (p) => (
  <Icon {...p}><circle cx="12" cy="8" r="4" /><path d="M4.5 21a7.5 7.5 0 0 1 15 0" /></Icon>
);

export const IconSlot = (p) => (
  <Icon {...p}><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M8 3v4M16 3v4M3 10h18M12 13v5M9.5 15.5h5" /></Icon>
);

export const IconTrend = (p) => (
  <Icon {...p}><path d="M3 17.5 9.5 11l4 4L21 7" /><path d="M15.5 7H21v5.5" /></Icon>
);
