import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { LandingPage } from "@/pages/landing";
import { ProfilePage } from "@/pages/profile";
import { AssistantPage } from "@/pages/assistant";
import { AuthPage } from "@/pages/auth";
import { OnboardingPage } from "@/pages/onboarding";
import { DoctorDashboardPage, DoctorCasePage } from "@/pages/doctor";
import { AdminPage } from "@/pages/admin";
import { NotFound } from "@/pages/not-found"
import { RoleRoute, PublicOnlyRoute, CabinetRedirect } from "./protected-router.jsx";


export default function AppRouter() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<LandingPage/>}/>
                <Route path="/cabinet" element={<CabinetRedirect/>}/>

                <Route element={<PublicOnlyRoute />}>
                    <Route path="/auth" element={<AuthPage/>}/>
                </Route>

                <Route element={<RoleRoute roles={["patient"]} allowMissingProfile />}>
                    <Route path="/onboarding" element={<OnboardingPage/>}/>
                </Route>

                <Route element={<RoleRoute roles={["patient"]} />}>
                    <Route path="/profile" element={<ProfilePage/>}/>
                    <Route path="/assistant" element={<AssistantPage/>}/>
                    <Route path="/assistant/:conversationId" element={<AssistantPage/>}/>
                </Route>

                <Route element={<RoleRoute roles={["doctor"]} />}>
                    <Route path="/doctor" element={<DoctorDashboardPage/>}/>
                    <Route path="/doctor/cases/:caseId" element={<DoctorCasePage/>}/>
                </Route>

                <Route element={<RoleRoute roles={["admin"]} />}>
                    <Route path="/admin" element={<AdminPage/>}/>
                </Route>

                <Route path="/chat/*" element={<Navigate to="/assistant" replace/>}/>
                <Route path="/landing" element={<Navigate to="/" replace/>}/>
                <Route path="*" element={<NotFound/>}/>
            </Routes>
        </BrowserRouter>
    )
}
