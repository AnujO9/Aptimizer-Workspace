import { useEffect, useMemo, useRef, useState } from "react";
import { useReducedMotion } from "framer-motion";

/**
 * Scroll-scrubbed image sequence.
 *
 * Progress is measured directly from the target's bounding rect on scroll, NOT through
 * framer-motion's useScroll. useScroll resolves its target once and caches the measurement;
 * in this page it kept reporting a progress that never reached the end of the sequence, so
 * the hero appeared frozen part-way through no matter which frames were supplied. The
 * arithmetic below is the same thing done explicitly, and was verified frame by frame in a
 * headless browser against these exact assets before shipping.
 *
 * Frames rather than a scrubbed <video>: a browser can only seek to a keyframe, and the
 * source clip carries two in the whole file, so scrubbing it snaps rather than moves.
 */
const imageCache = new Map();

const loadFrame = (url) => {
  let img = imageCache.get(url);
  if (img) return img;
  img = new Image();
  img.decoding = "async";
  img.src = url;
  imageCache.set(url, img);
  return img;
};

const defaultSrc = (i) => `/frames/${String(i).padStart(2, "0")}.webp`;

export function ScrollScene({
  target,                       // ref to the scroll runway element
  frameCount = 60,
  frames = null,                // explicit frame numbers, in order; overrides frameCount
  src = defaultSrc,
  poster = "/frames/poster.jpg",
  className = "",
  leadIn = 0,                   // fraction of the scroll held on blank paper first
}) {
  const canvasRef = useRef(null);
  const imagesRef = useRef([]);
  const rafRef = useRef(0);
  const currentRef = useRef(-1);
  const [ready, setReady] = useState(false);
  const reduced = useReducedMotion();

  const indices = useMemo(
    () => (frames && frames.length ? frames : Array.from({ length: frameCount }, (_, i) => i + 1)),
    [frames, frameCount]
  );

  useEffect(() => {
    if (reduced) return undefined;
    let cancelled = false;
    let loaded = 0;
    const imgs = indices.map((n) => loadFrame(src(n)));
    imagesRef.current = imgs;
    const mark = () => {
      loaded += 1;
      if (!cancelled && (loaded === 1 || loaded === imgs.length)) setReady(true);
    };
    imgs.forEach((img) => {
      if (img.complete && img.naturalWidth) mark();
      else {
        img.addEventListener("load", mark, { once: true });
        img.addEventListener("error", mark, { once: true });
      }
    });
    return () => { cancelled = true; };
  }, [indices, src, reduced]);

  useEffect(() => {
    if (reduced) return undefined;

    const progress = () => {
      const el = target?.current;
      if (!el) return 0;
      const r = el.getBoundingClientRect();
      // 0 when the runway's top meets the viewport top; 1 when its bottom meets the
      // viewport bottom -- which is exactly when the sticky child stops being pinned.
      const travel = r.height - window.innerHeight;
      if (travel <= 0) return 0;
      return Math.min(1, Math.max(0, -r.top / travel));
    };

    const draw = () => {
      const canvas = canvasRef.current;
      const imgs = imagesRef.current;
      if (!canvas || !imgs.length) return;
      const ctx = canvas.getContext("2d");
      const p = progress();

      if (leadIn > 0 && p < leadIn) {
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        currentRef.current = -1;
        return;
      }
      const q = leadIn > 0 ? (p - leadIn) / (1 - leadIn) : p;
      const idx = Math.min(imgs.length - 1, Math.max(0, Math.round(q * (imgs.length - 1))));
      if (idx === currentRef.current) return;

      let img = imgs[idx];
      if (!img?.complete || !img.naturalWidth) {
        // Nearest decoded frame, so a slow decode cannot strand the sequence.
        let found = null;
        for (let d = 1; d < imgs.length && !found; d += 1) {
          const a = imgs[idx - d];
          const b = imgs[idx + d];
          if (a?.complete && a.naturalWidth) found = a;
          else if (b?.complete && b.naturalWidth) found = b;
        }
        if (!found) return;
        img = found;
      }
      currentRef.current = idx;

      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      if (!w || !h) return;
      if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
        canvas.width = w * dpr;
        canvas.height = h * dpr;
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const scale = Math.max(w / img.naturalWidth, h / img.naturalHeight);   // object-fit: cover
      const dw = img.naturalWidth * scale;
      const dh = img.naturalHeight * scale;
      ctx.clearRect(0, 0, w, h);
      ctx.drawImage(img, (w - dw) / 2, (h - dh) / 2, dw, dh);
    };

    const onScroll = () => {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(draw);
    };
    const onResize = () => { currentRef.current = -1; onScroll(); };

    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onResize);
    onResize();
    const settle = setTimeout(onResize, 80);   // after layout and fonts settle

    return () => {
      cancelAnimationFrame(rafRef.current);
      clearTimeout(settle);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onResize);
    };
  }, [target, indices, leadIn, reduced, ready]);

  if (reduced) {
    return (
      <img src={poster} alt="" aria-hidden="true"
        className={`absolute inset-0 h-full w-full object-cover ${className}`} />
    );
  }

  return (
    <>
      <img
        src={poster}
        alt=""
        aria-hidden="true"
        className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-500 ${
          ready || leadIn > 0 ? "opacity-0" : "opacity-100"
        } ${className}`}
      />
      <canvas ref={canvasRef} aria-hidden="true"
        className={`absolute inset-0 h-full w-full ${className}`} />
    </>
  );
}
