import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ActionTracker from "./pages/ActionTracker";
import AppointmentDetail from "./pages/AppointmentDetail";
import AppointmentQueue from "./pages/AppointmentQueue";
import ClinicUtilization from "./pages/ClinicUtilization";
import CommandCenter from "./pages/CommandCenter";
import ProviderSchedule from "./pages/ProviderSchedule";
import SearchPage from "./pages/SearchPage";
import WaitlistManager from "./pages/WaitlistManager";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<CommandCenter />} />
        <Route path="/queue" element={<AppointmentQueue />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/appointments/:id" element={<AppointmentDetail />} />
        <Route path="/waitlist" element={<WaitlistManager />} />
        <Route path="/providers" element={<ProviderSchedule />} />
        <Route path="/clinics" element={<ClinicUtilization />} />
        <Route path="/actions" element={<ActionTracker />} />
      </Routes>
    </Layout>
  );
}
