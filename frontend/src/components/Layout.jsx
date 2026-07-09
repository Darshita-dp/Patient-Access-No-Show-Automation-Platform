import { NavLink, useLocation } from "react-router-dom";
import {
  IconBuilding, IconCalendar, IconDashboard, IconQueue, IconSearch,
  IconTasks, IconWaitlist,
} from "./Icons";

const NAV = [
  { section: "Operations" },
  { to: "/", label: "Command Center", icon: IconDashboard, title: "Command Center", subtitle: "Today's access risk, open slots, and staff workload at a glance" },
  { to: "/queue", label: "Work Queue", icon: IconQueue, title: "Appointment Work Queue", subtitle: "Prioritized outreach list with risk, actions, and reminder status" },
  { to: "/search", label: "Patient Search", icon: IconSearch, title: "Patient & Appointment Search", subtitle: "Find any patient or appointment across the schedule" },
  { section: "Access Management" },
  { to: "/waitlist", label: "Waitlist Manager", icon: IconWaitlist, title: "Waitlist Manager", subtitle: "Match open and released slots to waiting patients" },
  { to: "/providers", label: "Provider Schedules", icon: IconCalendar, title: "Provider Schedule View", subtitle: "Daily bookings, no-show risk, and open capacity by provider" },
  { to: "/clinics", label: "Clinic Utilization", icon: IconBuilding, title: "Clinic Utilization", subtitle: "Capacity, leakage, and recovered-slot performance by clinic" },
  { section: "Management" },
  { to: "/actions", label: "Action Tracker", icon: IconTasks, title: "Manager Action Tracker", subtitle: "Staff outreach tasks: pending, overdue, and completed" },
];

function currentMeta(pathname) {
  const links = NAV.filter((n) => n.to);
  if (pathname.startsWith("/appointments/")) {
    return { title: "Appointment Detail", subtitle: "Risk drivers, outreach history, and replacement options" };
  }
  const exact = links.find((n) => n.to === pathname);
  return exact || links.find((n) => n.to !== "/" && pathname.startsWith(n.to)) || links[0];
}

export default function Layout({ children }) {
  const { pathname } = useLocation();
  const meta = currentMeta(pathname);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark">+</div>
          <div>
            <div className="brand-name">Patient Access</div>
            <div className="brand-sub">No-Show Automation Platform</div>
          </div>
        </div>
        <nav>
          {NAV.map((item, i) =>
            item.section ? (
              <div key={i} className="nav-section-label">{item.section}</div>
            ) : (
              <NavLink key={item.to} to={item.to} end={item.to === "/"} className="nav-link">
                <item.icon />
                {item.label}
              </NavLink>
            )
          )}
        </nav>
        <div className="sidebar-foot">
          Scheduling Operations Suite<br />
          Synthetic demonstration data
        </div>
      </aside>

      <div className="main-col">
        <header className="topbar">
          <div>
            <h1 className="page-title">{meta.title}</h1>
            <div className="page-subtitle">{meta.subtitle}</div>
          </div>
          <div className="topbar-right">
            <div className="user-chip">
              <div className="user-avatar">SK</div>
              <div>
                <div className="name">Sandra Kim</div>
                <div className="role">Patient Access Manager</div>
              </div>
            </div>
          </div>
        </header>
        <main className="page-body">{children}</main>
      </div>
    </div>
  );
}
