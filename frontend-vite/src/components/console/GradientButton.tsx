// GradientButton — layered gradient border + glow CTA, adapted from KokonutUI
// (https://kokonutui.com, MIT). Pure CSS (no shadcn dependency): the border is
// a 2px gradient ring, the interior is stacked base/overlay/accent gradients
// with an inset glow, the label is gradient-clipped text with a drop shadow,
// and a sweep overlay fades in on hover.
import { type ButtonHTMLAttributes, type ReactNode } from 'react';
import clsx from 'clsx';

type GradientButtonVariant = 'cyan' | 'gold';

interface GradientButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: GradientButtonVariant;
  children: ReactNode;
}

export default function GradientButton({
  variant = 'cyan',
  className,
  children,
  ...rest
}: GradientButtonProps) {
  return (
    <button
      type="button"
      className={clsx('gradient-btn', `gradient-btn--${variant}`, className)}
      {...rest}
    >
      <span className="gradient-btn__label">{children}</span>
    </button>
  );
}
