import { Navigate, Route, Routes } from "react-router-dom";
import { Header } from "./components/Header";
import { ErrorState, Skeleton } from "./components/States";
import { isAdmin, useSessionQuery, ViewerProvider } from "./lib/session";
import { lastSport, useSportTheme } from "./lib/sportContext";
import { AccountPage } from "./pages/AccountPage";
import { HistoryPage } from "./pages/HistoryPage";
import { LoginPage } from "./pages/LoginPage";
import { MyBetsPage } from "./pages/MyBetsPage";
import { PerformancePage } from "./pages/PerformancePage";
import { UsersPage } from "./pages/UsersPage";
import { DayPage as FutbolDayPage } from "./sports/futbol/DayPage";
import { RoundPage } from "./sports/futbol/RoundPage";
import { DayPage as NbaDayPage } from "./sports/nba/DayPage";

/** Todo pide sesión: sin ella, cualquier ruta muestra "Entrar" y, al entrar, se queda en la ruta pedida. */
export function App() {
  useSportTheme();
  const session = useSessionQuery();

  if (session.isPending) {
    return (
      <main className="login-page" aria-busy="true" aria-label="Cargando">
        <Skeleton height={320} width={380} />
      </main>
    );
  }
  if (session.isError) {
    return (
      <main className="login-page">
        <ErrorState message={(session.error as Error).message} onRetry={() => session.refetch()} />
      </main>
    );
  }
  if (!session.data) return <LoginPage />;

  const viewer = session.data;
  return (
    <ViewerProvider value={viewer}>
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
          <Route path="/cuenta" element={<AccountPage />} />
          {isAdmin(viewer) && <Route path="/usuarios" element={<UsersPage />} />}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </ViewerProvider>
  );
}
