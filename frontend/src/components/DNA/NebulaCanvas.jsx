import { useRef, useEffect, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import * as THREE from 'three';

function NebulaParticles({ pattern, isAnimated = true }) {
  const pointsRef = useRef();
  
  const { positions, colors, sizes } = useMemo(() => {
    if (!pattern) {
      return { positions: new Float32Array(), colors: new Float32Array(), sizes: new Float32Array() };
    }
    
    const particleCount = pattern.particle_count || 200;
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const sizes = new Float32Array(particleCount);
    
    const seed = pattern.seed || 42;
    const seededRandom = (i) => {
      const x = Math.sin(seed + i * 9999) * 10000;
      return x - Math.floor(x);
    };
    
    const baseColor = hexToRgb(pattern.base_color || '#1a1a2e');
    const accentColor = hexToRgb(pattern.accent_color || '#0f3460');
    
    for (let i = 0; i < particleCount; i++) {
      const i3 = i * 3;
      
      const angle = seededRandom(i * 3) * Math.PI * 2;
      const radius = -Math.log(seededRandom(i * 3 + 1)) * 3;
      const height = (seededRandom(i * 3 + 2) - 0.5) * 2;
      
      positions[i3] = radius * Math.cos(angle);
      positions[i3 + 1] = height;
      positions[i3 + 2] = radius * Math.sin(angle);
      
      const t = seededRandom(i * 3 + 1);
      colors[i3] = baseColor.r * (1 - t) + accentColor.r * t;
      colors[i3 + 1] = baseColor.g * (1 - t) + accentColor.g * t;
      colors[i3 + 2] = baseColor.b * (1 - t) + accentColor.b * t;
      
      sizes[i] = seededRandom(i * 3 + 2) * 0.15 + 0.02;
    }
    
    return { positions, colors, sizes };
  }, [pattern]);
  
  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geo.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
    return geo;
  }, [positions, colors, sizes]);
  
  const material = useMemo(() => {
    return new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uTurbulence: { value: pattern?.turbulence || 0.3 },
        uRotationSpeed: { value: pattern?.rotation_speed || 0.01 }
      },
      vertexShader: `
        attribute float size;
        attribute vec3 color;
        uniform float uTime;
        uniform float uTurbulence;
        uniform float uRotationSpeed;
        varying vec3 vColor;
        varying float vOpacity;
        
        float noise(vec3 p) {
          return fract(sin(dot(p, vec3(12.9898, 78.233, 45.543))) * 43758.5453);
        }
        
        void main() {
          vColor = color;
          vOpacity = size * 5.0;
          
          vec3 pos = position;
          
          float angle = uTime * uRotationSpeed;
          float cosA = cos(angle);
          float sinA = sin(angle);
          float x = pos.x * cosA - pos.z * sinA;
          float z = pos.x * sinA + pos.z * cosA;
          pos.x = x;
          pos.z = z;
          
          float n = noise(pos + uTime * 0.1) * uTurbulence;
          pos.y += (n - 0.5) * 0.2;
          
          vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
          gl_PointSize = size * 200.0 / -mvPosition.z;
          gl_Position = projectionMatrix * mvPosition;
        }
      `,
      fragmentShader: `
        varying vec3 vColor;
        varying float vOpacity;
        
        void main() {
          float dist = length(gl_PointCoord - vec2(0.5));
          if (dist > 0.5) discard;
          
          float alpha = 1.0 - smoothstep(0.0, 0.5, dist);
          gl_FragColor = vec4(vColor, alpha * 0.8);
        }
      `,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
  }, [pattern]);
  
  useFrame((state) => {
    if (pointsRef.current && isAnimated) {
      material.uniforms.uTime.value = state.clock.elapsedTime;
    }
  });
  
  return (
    <points ref={pointsRef} geometry={geometry} material={material} />
  );
}

function NebulaBackground({ pattern }) {
  const bgColor = pattern?.base_color || '#1a1a2e';
  const accentColor = pattern?.accent_color || '#0f3460';
  
  return (
    <color attach="background" args={[bgColor]} />
  );
}

function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16) / 255,
    g: parseInt(result[2], 16) / 255,
    b: parseInt(result[3], 16) / 255
  } : { r: 0.1, g: 0.1, b: 0.18 };
}

export default function NebulaCanvas({ pattern, isAnimated = true, className = '' }) {
  return (
    <div className={`w-full h-full ${className}`}>
      <Canvas camera={{ position: [0, 0, 6], fov: 60 }}>
        <NebulaBackground pattern={pattern} />
        <ambientLight intensity={0.5} />
        <NebulaParticles pattern={pattern} isAnimated={isAnimated} />
        <Stars radius={100} depth={50} count={1000} factor={4} saturation={0} fade speed={1} />
        <OrbitControls enableZoom={false} enablePan={false} autoRotate={isAnimated} autoRotateSpeed={0.5} />
      </Canvas>
    </div>
  );
}
