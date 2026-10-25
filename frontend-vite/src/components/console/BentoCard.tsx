// BentoCard — 3D tilt card with staggered entrance, adapted from KokonutUI
// (https://kokonutui.com, MIT). The card rotates subtly toward the cursor
// (preserve-3d, spring), lifts on hover, and fades in when scrolled into
// view. Parent grid uses `gridVariants` to stagger the children.
import { type CSSProperties, type ReactNode } from 'react';
import { motion, useMotionValue, useTransform, type Variants } from 'motion/react';
import clsx from 'clsx';

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export const cardVariants: Variants = {
  hidden: { opacity: 0, y: 18 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' } },
};

export const gridVariants: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.12, delayChildren: 0.05 } },
};

export default function BentoCard({
  children,
  className,
  style,
}: {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotateX = useTransform(y, [-100, 100], [1.6, -1.6]);
  const rotateY = useTransform(x, [-100, 100], [-1.6, 1.6]);

  const onMouseMove = (event: React.MouseEvent<HTMLDivElement>) => {
    if (prefersReducedMotion()) return;
    const rect = event.currentTarget.getBoundingClientRect();
    x.set((event.clientX / rect.width - 0.5) * 100);
    y.set((event.clientY / rect.height - 0.5) * 100);
  };

  const onMouseLeave = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <motion.div
      className={clsx('bento-tilt', className)}
      style={{ rotateX, rotateY, transformStyle: 'preserve-3d', ...style }}
      transition={{ type: 'spring', stiffness: 300, damping: 22 }}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      whileHover={prefersReducedMotion() ? undefined : { y: -4 }}
      variants={cardVariants}
    >
      {children}
    </motion.div>
  );
}
