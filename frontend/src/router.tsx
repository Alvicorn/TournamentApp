import { lazy, Suspense } from "react";
import { createBrowserRouter } from "react-router-dom";
import { AdminLayout } from "./layouts/AdminLayout";
import { JudgeLayout } from "./layouts/JudgeLayout";
import { PublicLayout } from "./layouts/PublicLayout";

const l = <T extends React.ComponentType>(fn: () => Promise<{ default: T }>) =>
  lazy(fn);

// Public
const PublicDashboard = l(() => import("./pages/public/PublicDashboard"));
const DivisionView = l(() => import("./pages/public/DivisionView"));
const DivisionPrint = l(() => import("./pages/public/DivisionPrint"));
const CompetitorProfile = l(() => import("./pages/public/CompetitorProfile"));
const MatchPrint = l(() => import("./pages/public/MatchPrint"));
const SubscriptionsPage = l(() => import("./pages/public/SubscriptionsPage"));

// Admin
const AdminLogin = l(() => import("./pages/admin/AdminLogin"));
const AdminHome = l(() => import("./pages/admin/AdminHome"));
const AdminSetup = l(() => import("./pages/admin/AdminSetup"));
const AdminJudges = l(() => import("./pages/admin/AdminJudges"));
const AdminParticipants = l(() => import("./pages/admin/AdminParticipants"));
const AdminDivisions = l(() => import("./pages/admin/AdminDivisions"));
const AdminDivisionDetail = l(() => import("./pages/admin/AdminDivisionDetail"));
const AdminBroadcasts = l(() => import("./pages/admin/AdminBroadcasts"));
const AdminBackups = l(() => import("./pages/admin/AdminBackups"));
const AdminActivity = l(() => import("./pages/admin/AdminActivity"));

// Judge
const JudgeLogin = l(() => import("./pages/judge/JudgeLogin"));
const JudgeHome = l(() => import("./pages/judge/JudgeHome"));
const JudgeDivision = l(() => import("./pages/judge/JudgeDivision"));
const JudgeMatch = l(() => import("./pages/judge/JudgeMatch"));
const JudgeMatchReview = l(() => import("./pages/judge/JudgeMatchReview"));
const NotFound = l(() => import("./pages/NotFound"));

const wrap = (el: JSX.Element) => <Suspense fallback={<div />}>{el}</Suspense>;

export const router = createBrowserRouter([
  {
    element: <PublicLayout />,
    children: [
      { path: "/", element: wrap(<PublicDashboard />) },
      { path: "/divisions/:id", element: wrap(<DivisionView />) },
      { path: "/divisions/:id/print", element: wrap(<DivisionPrint />) },
      { path: "/competitors/:id", element: wrap(<CompetitorProfile />) },
      { path: "/matches/:id/print", element: wrap(<MatchPrint />) },
      { path: "/subscriptions", element: wrap(<SubscriptionsPage />) },
    ],
  },
  { path: "/admin/login", element: wrap(<AdminLogin />) },
  {
    path: "/admin",
    element: <AdminLayout />,
    children: [
      { index: true, element: wrap(<AdminHome />) },
      { path: "setup", element: wrap(<AdminSetup />) },
      { path: "judges", element: wrap(<AdminJudges />) },
      { path: "participants", element: wrap(<AdminParticipants />) },
      { path: "divisions", element: wrap(<AdminDivisions />) },
      { path: "divisions/:id", element: wrap(<AdminDivisionDetail />) },
      { path: "broadcasts", element: wrap(<AdminBroadcasts />) },
      { path: "backups", element: wrap(<AdminBackups />) },
      { path: "activity", element: wrap(<AdminActivity />) },
    ],
  },
  { path: "/judge/login", element: wrap(<JudgeLogin />) },
  {
    path: "/judge",
    element: <JudgeLayout />,
    children: [
      { index: true, element: wrap(<JudgeHome />) },
      { path: "divisions/:id", element: wrap(<JudgeDivision />) },
      { path: "matches/:id", element: wrap(<JudgeMatch />) },
      { path: "matches/:id/review", element: wrap(<JudgeMatchReview />) },
    ],
  },
  { path: "*", element: wrap(<NotFound />) },
]);
