import { useEffect, useState } from "react";

function formatTime(d: Date): string {
  return d.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export default function Clock() {
  const [time, setTime] = useState(() => formatTime(new Date()));

  useEffect(() => {
    // Align to the next full second for accuracy
    const now = Date.now();
    const delay = 1000 - (now % 1000);
    let intervalId: ReturnType<typeof setInterval>;

    const timeoutId = setTimeout(() => {
      setTime(formatTime(new Date()));
      intervalId = setInterval(() => {
        setTime(formatTime(new Date()));
      }, 1000);
    }, delay);

    return () => {
      clearTimeout(timeoutId);
      clearInterval(intervalId);
    };
  }, []);

  return <time className="clock">{time}</time>;
}
