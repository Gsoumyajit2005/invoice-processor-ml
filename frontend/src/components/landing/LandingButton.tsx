"use client";

import React from "react";
import { cn } from "@/lib/format";

export interface LandingButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "ghost" | "secondary";
  size?: "default" | "sm" | "lg" | "icon";
  asChild?: boolean;
}

export const LandingButton = React.forwardRef<
  HTMLButtonElement,
  LandingButtonProps
>(({ className, variant = "default", size = "default", ...props }, ref) => {
  const base =
    "inline-flex items-center justify-center gap-2 whitespace-nowrap font-medium transition-all duration-300 disabled:pointer-events-none disabled:opacity-50 outline-none focus-visible:ring-2 focus-visible:ring-accent cursor-pointer";

  const variants = {
    default:
      "bg-foreground text-background hover:bg-foreground/90 shadow-sm",
    outline:
      "border border-foreground/20 text-foreground bg-transparent hover:bg-foreground/5",
    ghost:
      "text-foreground hover:bg-foreground/10",
    secondary:
      "bg-muted text-foreground hover:bg-muted/80",
  };

  const sizes = {
    default: "h-10 px-5 py-2 text-sm rounded-full",
    sm: "h-8 px-4 text-xs rounded-full",
    lg: "h-14 px-8 text-base rounded-full",
    icon: "h-9 w-9 rounded-full",
  };

  return (
    <button
      ref={ref}
      className={cn(base, variants[variant], sizes[size], className)}
      {...props}
    />
  );
});

LandingButton.displayName = "LandingButton";
