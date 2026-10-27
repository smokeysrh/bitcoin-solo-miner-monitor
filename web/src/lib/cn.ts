import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Join class names and let the last Tailwind utility win (`cn('p-2', props.class)`). */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}
