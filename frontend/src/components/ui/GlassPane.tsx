import { cn } from "@/lib/utils";
import { motion, HTMLMotionProps } from "framer-motion";

interface GlassPaneProps extends HTMLMotionProps<"div"> {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}

export function GlassPane({ children, className, delay = 0, ...props }: GlassPaneProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        "glass-pane overflow-hidden relative",
        className
      )}
      {...props}
    >
      {/* Subtle top glare effect */}
      <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/20 to-transparent" />
      {children}
    </motion.div>
  );
}
