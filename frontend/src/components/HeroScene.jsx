import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float } from '@react-three/drei';
import * as THREE from 'three';

// Rotating wireframe and illuminated data cube
function DataCube({ reduceMotion }) {
  const meshRef = useRef();
  const innerRef = useRef();

  useFrame((state, delta) => {
    if (!reduceMotion && meshRef.current && innerRef.current) {
      meshRef.current.rotation.x += delta * 0.25;
      meshRef.current.rotation.y += delta * 0.35;
      innerRef.current.rotation.x -= delta * 0.4;
      innerRef.current.rotation.y -= delta * 0.2;
    }
  });

  return (
    <group position={[0, 0, 0]}>
      {/* Outer transparent wireframe cube */}
      <mesh ref={meshRef}>
        <boxGeometry args={[2.4, 2.4, 2.4]} />
        <meshStandardMaterial
          color="#06b6d4"
          wireframe
          transparent
          opacity={0.45}
          roughness={0.2}
          metalness={0.8}
        />
      </mesh>

      {/* Inner glowing core */}
      <mesh ref={innerRef}>
        <boxGeometry args={[1.3, 1.3, 1.3]} />
        <meshStandardMaterial
          color="#3b82f6"
          roughness={0.1}
          metalness={0.9}
          emissive="#1d4ed8"
          emissiveIntensity={0.6}
        />
      </mesh>
    </group>
  );
}

// Lightweight floating data nodes / particles
function FloatingParticles({ count = 35, reduceMotion }) {
  const points = useMemo(() => {
    const coords = [];
    for (let i = 0; i < count; i++) {
      coords.push({
        position: [
          (Math.random() - 0.5) * 8,
          (Math.random() - 0.5) * 5,
          (Math.random() - 0.5) * 4,
        ],
        size: Math.random() * 0.08 + 0.04,
      });
    }
    return coords;
  }, [count]);

  return (
    <group>
      {points.map((pt, i) => (
        <Float
          key={i}
          speed={reduceMotion ? 0 : 1.5}
          rotationIntensity={reduceMotion ? 0 : 0.8}
          floatIntensity={reduceMotion ? 0 : 1.5}
        >
          <mesh position={pt.position}>
            <sphereGeometry args={[pt.size, 12, 12]} />
            <meshStandardMaterial
              color="#38bdf8"
              emissive="#0284c7"
              emissiveIntensity={0.8}
              roughness={0.3}
            />
          </mesh>
        </Float>
      ))}
    </group>
  );
}

export default function HeroScene({ reduceMotion = false }) {
  return (
    <div className="absolute inset-0 pointer-events-none opacity-60 overflow-hidden">
      <Canvas
        camera={{ position: [0, 0, 6], fov: 45 }}
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
        dpr={[1, 1.5]}
      >
        <ambientLight intensity={0.7} />
        <directionalLight position={[10, 10, 5]} intensity={1.2} color="#38bdf8" />
        <pointLight position={[-10, -5, -5]} intensity={0.8} color="#a855f7" />

        <DataCube reduceMotion={reduceMotion} />
        <FloatingParticles reduceMotion={reduceMotion} />
      </Canvas>
    </div>
  );
}
