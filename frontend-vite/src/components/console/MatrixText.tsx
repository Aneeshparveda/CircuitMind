// MatrixText — binary "decode rain" hero wordmark, adapted from KokonutUI
// (https://kokonutui.com, MIT). Each letter flashes a random 0/1 in matrix
// green, then settles to the final glyph. Deterministic per letter, pure
// client animation — no network, no canvas, no heavy deps beyond motion.
import { motion } from 'motion/react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import clsx from 'clsx';

interface LetterState {
  char: string;
  isMatrix: boolean;
  isSpace: boolean;
}

interface MatrixTextProps {
  text?: string;
  className?: string;
  initialDelay?: number;
  letterAnimationDuration?: number;
  letterInterval?: number;
  matrixColor?: string;
  settleColor?: string;
}

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export default function MatrixText({
  text = 'CIRCUITMIND',
  className = '',
  initialDelay = 320,
  letterAnimationDuration = 380,
  letterInterval = 82,
  matrixColor = '#3dff8e',
  settleColor = '#efffff',
}: MatrixTextProps) {
  const [letters, setLetters] = useState<LetterState[]>(() =>
    text.split('').map((char) => ({ char, isMatrix: false, isSpace: char === ' ' }))
  );
  const [isAnimating, setIsAnimating] = useState(false);

  const getRandomChar = useCallback(() => (Math.random() > 0.5 ? '1' : '0'), []);

  const animateLetter = useCallback(
    (index: number) => {
      if (index >= text.length) return;
      requestAnimationFrame(() => {
        setLetters((prev) => {
          const next = [...prev];
          if (!next[index].isSpace) {
            next[index] = { ...next[index], char: getRandomChar(), isMatrix: true };
          }
          return next;
        });
        setTimeout(() => {
          setLetters((prev) => {
            const next = [...prev];
            next[index] = { ...next[index], char: text[index], isMatrix: false };
            return next;
          });
        }, letterAnimationDuration);
      });
    },
    [getRandomChar, text, letterAnimationDuration]
  );

  const startAnimation = useCallback(() => {
    if (isAnimating || prefersReducedMotion()) return;
    setIsAnimating(true);
    let currentIndex = 0;
    const animate = () => {
      if (currentIndex >= text.length) {
        setIsAnimating(false);
        return;
      }
      animateLetter(currentIndex);
      currentIndex += 1;
      setTimeout(animate, letterInterval);
    };
    animate();
  }, [animateLetter, text, isAnimating, letterInterval]);

  useEffect(() => {
    if (prefersReducedMotion()) return undefined;
    const timer = setTimeout(startAnimation, initialDelay);
    return () => clearTimeout(timer);
    // Run the decode once on mount (initialDelay is intentionally static).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const motionVariants = useMemo(
    () => ({
      matrix: {
        color: matrixColor,
        textShadow: `0 0 14px ${matrixColor}80, 0 0 4px ${matrixColor}55`,
      },
      normal: {
        color: settleColor,
        textShadow: '0 2px 18px rgba(111, 227, 229, 0.18)',
      },
    }),
    [matrixColor, settleColor]
  );

  return (
    <div aria-label={`${text} — matrix decode animation`} className={clsx('matrix-hero', className)}>
      <div className="matrix-hero__letters">
        {letters.map((letter, index) => (
          <motion.div
            key={index}
            animate={letter.isMatrix ? 'matrix' : 'normal'}
            initial="normal"
            variants={motionVariants}
            transition={{ duration: 0.14, ease: 'easeInOut' }}
            className={clsx('matrix-hero__letter', letter.isSpace && 'matrix-hero__letter--space')}
            style={{ fontVariantNumeric: 'tabular-nums' }}
          >
            {letter.isSpace ? '\u00A0' : letter.char}
          </motion.div>
        ))}
      </div>
    </div>
  );
}
