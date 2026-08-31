/**
 * Blueprint grid — what the hero shows before the drawing sequence starts.
 *
 * The lead-in used to hold blank paper, which read as an empty page rather than as a
 * drawing about to happen. Drawn as an SVG rather than shipped as an image: it is a few
 * hundred bytes, stays sharp at any width, and needs no asset in public/.
 */
export default function Blueprint({ className = "" }) {
  return (
    <svg
      className={`absolute inset-0 h-full w-full ${className}`}
      preserveAspectRatio="xMidYMid slice"
      viewBox="0 0 1400 700"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="bp-sky" x1="0" y1="0" x2="0.35" y2="1">
          <stop offset="0%" stopColor="#1F9CF0" />
          <stop offset="55%" stopColor="#1477D6" />
          <stop offset="100%" stopColor="#1060B4" />
        </linearGradient>

        {/* Fine 10px squares, with a heavier line every 50 — standard drafting paper. */}
        <pattern id="bp-fine" width="10" height="10" patternUnits="userSpaceOnUse">
          <path d="M10 0H0V10" fill="none" stroke="#FFFFFF" strokeOpacity="0.16"
            strokeWidth="0.6" />
        </pattern>
        <pattern id="bp-major" width="50" height="50" patternUnits="userSpaceOnUse">
          <rect width="50" height="50" fill="url(#bp-fine)" />
          <path d="M50 0H0V50" fill="none" stroke="#FFFFFF" strokeOpacity="0.34"
            strokeWidth="1" />
        </pattern>

        {/* Registration dots on every fifth major line. */}
        <pattern id="bp-dots" width="250" height="250" patternUnits="userSpaceOnUse">
          <circle cx="0" cy="0" r="2.2" fill="#FFFFFF" fillOpacity="0.55" />
          <circle cx="250" cy="0" r="2.2" fill="#FFFFFF" fillOpacity="0.55" />
          <circle cx="0" cy="250" r="2.2" fill="#FFFFFF" fillOpacity="0.55" />
          <circle cx="250" cy="250" r="2.2" fill="#FFFFFF" fillOpacity="0.55" />
        </pattern>

        {/* Corners sit slightly darker, the way a large sheet does under even light. */}
        <radialGradient id="bp-vignette" cx="50%" cy="45%" r="75%">
          <stop offset="60%" stopColor="#000000" stopOpacity="0" />
          <stop offset="100%" stopColor="#0A3F79" stopOpacity="0.45" />
        </radialGradient>
      </defs>

      <rect width="1400" height="700" fill="url(#bp-sky)" />
      <rect width="1400" height="700" fill="url(#bp-major)" />
      <rect width="1400" height="700" fill="url(#bp-dots)" />
      <rect width="1400" height="700" fill="url(#bp-vignette)" />

      {/* Sheet border, inset like a title-block frame. */}
      <rect x="18" y="18" width="1364" height="664" fill="none" stroke="#FFFFFF"
        strokeOpacity="0.55" strokeWidth="2" />
      <rect x="30" y="30" width="1340" height="640" fill="none" stroke="#FFFFFF"
        strokeOpacity="0.22" strokeWidth="1" />
    </svg>
  );
}
