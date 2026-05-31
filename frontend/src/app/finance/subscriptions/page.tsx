import { redirect } from "next/navigation";

export default function SubscriptionsRedirectPage() {
  redirect("/finance?tab=langganan");
}
