import { redirect } from "next/navigation";

/** Redirect root path to dashboard page. */
export default function HomePage() {
  redirect("/dashboard");
}
