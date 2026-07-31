import { redirect } from "next/navigation";

// The bare domain is the public storefront's front door. Staff use /login for the admin.
export default function Home() {
  redirect("/store");
}
