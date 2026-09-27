"use client";

import React, { useEffect, useRef } from "react";

export function WireframeTunnel() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = canvas.parentElement?.clientWidth || 600);
    let height = (canvas.height = canvas.parentElement?.clientHeight || 600);

    const handleResize = () => {
      if (!canvas || !canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.clientWidth;
      height = canvas.height = canvas.parentElement.clientHeight;
    };

    window.addEventListener("resize", handleResize);

    // Mouse tilt tracking
    let targetMouseX = 0;
    let targetMouseY = 0;
    let mouseX = 0;
    let mouseY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      targetMouseX = x * 80;
      targetMouseY = y * 80;
    };

    window.addEventListener("mousemove", handleMouseMove);

    // Tunnel geometry configuration
    const numRings = 24;
    const numSectors = 28;
    const tunnelDepth = 1200;
    let offsetZ = 0;

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Smooth mouse lerp
      mouseX += (targetMouseX - mouseX) * 0.05;
      mouseY += (targetMouseY - mouseY) * 0.05;

      const cx = width / 2 + mouseX;
      const cy = height / 2 + mouseY;

      // Subtle background vignette
      const bgGrad = ctx.createRadialGradient(cx, cy, 10, cx, cy, width * 0.7);
      bgGrad.addColorStop(0, "rgba(20, 20, 20, 0.95)");
      bgGrad.addColorStop(0.6, "rgba(10, 10, 10, 0.98)");
      bgGrad.addColorStop(1, "rgba(5, 5, 5, 1)");
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, width, height);

      // Continuous forward camera motion
      offsetZ = (offsetZ + 1.2) % (tunnelDepth / numRings);

      // Store projected points for connecting rings and radials
      // points[ringIndex][sectorIndex] = { x, y, z, scale }
      const points: Array<Array<{ x: number; y: number; z: number; scale: number }>> = [];

      for (let i = 0; i < numRings; i++) {
        const ringPoints: Array<{ x: number; y: number; z: number; scale: number }> = [];
        // z position from near to far
        const z = 80 + i * (tunnelDepth / numRings) - offsetZ;
        const scale = 280 / z;

        // Radius expands hyperbolically to simulate tunnel tube
        const baseRadius = 240 + Math.pow(i / numRings, 1.4) * 480;

        for (let j = 0; j < numSectors; j++) {
          const angle = (j / numSectors) * Math.PI * 2;
          const px = Math.cos(angle) * baseRadius;
          const py = Math.sin(angle) * baseRadius;

          const projX = cx + px * scale;
          const projY = cy + py * scale;

          ringPoints.push({ x: projX, y: projY, z, scale });
        }
        points.push(ringPoints);
      }

      // Draw concentric rings
      for (let i = 0; i < numRings; i++) {
        const alpha = Math.max(0.08, Math.min(0.65, (numRings - i) / numRings));
        ctx.beginPath();
        for (let j = 0; j < numSectors; j++) {
          const pt = points[i][j];
          if (j === 0) ctx.moveTo(pt.x, pt.y);
          else ctx.lineTo(pt.x, pt.y);
        }
        ctx.closePath();
        ctx.strokeStyle = `rgba(220, 220, 220, ${alpha * 0.4})`;
        ctx.lineWidth = i < 4 ? 1.4 : 0.8;
        ctx.stroke();
      }

      // Draw radial lines connecting rings
      for (let j = 0; j < numSectors; j++) {
        ctx.beginPath();
        for (let i = 0; i < numRings; i++) {
          const pt = points[i][j];
          if (i === 0) ctx.moveTo(pt.x, pt.y);
          else ctx.lineTo(pt.x, pt.y);
        }
        ctx.strokeStyle = "rgba(180, 180, 180, 0.22)";
        ctx.lineWidth = 0.75;
        ctx.stroke();
      }

      // Draw glowing intersection points / nodes
      for (let i = 0; i < numRings; i += 1) {
        const alpha = Math.max(0.12, Math.min(0.85, (numRings - i) / numRings));
        for (let j = 0; j < numSectors; j++) {
          const pt = points[i][j];
          const nodeRadius = Math.max(0.8, Math.min(2.5, pt.scale * 1.8));

          // Occasional highlight nodes (crimson accent)
          const isAccent = (i * 7 + j * 3) % 13 === 0;

          ctx.beginPath();
          ctx.arc(pt.x, pt.y, nodeRadius, 0, Math.PI * 2);
          if (isAccent) {
            ctx.fillStyle = `rgba(255, 59, 48, ${alpha * 0.9})`;
          } else {
            ctx.fillStyle = `rgba(240, 240, 245, ${alpha * 0.75})`;
          }
          ctx.fill();
        }
      }

      // Subtle center vanishing point singularity glow
      const centerGrad = ctx.createRadialGradient(cx, cy, 2, cx, cy, 40);
      centerGrad.addColorStop(0, "rgba(255, 59, 48, 0.35)");
      centerGrad.addColorStop(0.4, "rgba(255, 255, 255, 0.15)");
      centerGrad.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = centerGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, 40, 0, Math.PI * 2);
      ctx.fill();

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className="relative w-full h-full min-h-[460px] md:min-h-[560px] overflow-hidden bg-[#0c0c0c] flex items-center justify-center">
      <canvas
        ref={canvasRef}
        className="w-full h-full block cursor-crosshair"
      />
      {/* Subtle overlay vignette grid */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_40%,#0c0c0c_95%)]" />
      {/* Decorative coordinate watermark */}
      <div className="absolute top-4 right-4 font-mono text-[10px] text-zinc-600 tracking-widest uppercase pointer-events-none select-none">
        GRID::3D_PROJECTION // LAT:45.02°
      </div>
      <div className="absolute bottom-4 left-4 font-mono text-[10px] text-zinc-600 tracking-wider pointer-events-none select-none">
        AST_NODES: 2,450 • TARJAN_SCC: O(V+E)
      </div>
    </div>
  );
}
