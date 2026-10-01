import { redirect } from "next/navigation";
import { getCurrentUser } from "@/lib/backend";
import { AdminDashboard } from "@/components/AdminDashboard";
import "./admin.css";

export default async function AdminPage() {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  if (!user.is_admin) redirect("/panel");
  return <AdminDashboard />;
}
