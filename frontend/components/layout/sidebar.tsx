import { ShieldCheck } from "lucide-react";

import { SidebarNav } from "@/components/layout/sidebar-nav";

export function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 border-r bg-sidebar md:flex md:flex-col">
      <div className="flex h-16 items-center gap-2 border-b px-6">
        <ShieldCheck className="h-5 w-5 text-primary" />
        <span className="font-semibold">AccessCore</span>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        <SidebarNav />
      </div>
    </aside>
  );
}
