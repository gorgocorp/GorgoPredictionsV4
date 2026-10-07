import { Navigate, Route, Routes } from "react-router-dom";
import { Header } from "./components/Header";
import { lastSport, useSportTheme } from "./lib/sportContext";
import { HistoryPage } from "./pages/HistoryPage";
import { MyBetsPage } from "./pages/MyBetsPage";
import { PerformancePage } from "./pages/PerformancePage";
import { DayPage as FutbolDayPage } from "./sports/futbol/DayPage";
import { RoundPage } from "./sports/futbol/RoundPage";
import { DayPage as NbaDayPage } from "./sports/nba/DayPage";

export function App() {
  useSportTheme();
  return (
    <>
      <Header />
      <main className="page">
        <Routes>
          <Route path="/" element={<Navigate to={`/${lastSport()}`} replace />} />
          <Route path="/nba" element={<NbaDayPage />} />
          <Route path="/futbol" element={<FutbolDayPage />} />
          <Route path="/futbol/jornada" element={<RoundPage />} />
          <Route path="/historial" element={<HistoryPage />} />
          <Route path="/mis-apuestas" element={<MyBetsPage />} />
          <Route path="/rendimiento" element={<PerformancePage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}
