import { useRef, useMemo, useEffect, useState, useCallback } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Text, Float, Line, Html } from '@react-three/drei';
import * as THREE from 'three';

const COLORS = [
  '#6366f1',
  '#ec4899',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#06b6d4',
  '#8b5cf6',
  '#f97316'
];

const getColor = (group) => {
  return COLORS[group % COLORS.length];
};

function Node({ 
  position, 
  data, 
  isSelected, 
  onSelect, 
  isPulsing,
  neighbors,
  showLabels 
}) {
  const meshRef = useRef();
  const glowRef = useRef();
  const [hovered, setHovered] = useState(false);
  
  const size = data.size || 1;
  const baseScale = 0.15 + (size * 0.02);
  const scale = hovered ? baseScale * 1.5 : baseScale;
  const color = getColor(data.group || 0);
  
  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.scale.lerp(
        new THREE.Vector3(scale, scale, scale),
        0.1
      );
      
      if (isPulsing) {
        const pulse = 1 + Math.sin(state.clock.elapsedTime * 3) * 0.3;
        meshRef.current.scale.set(
          scale * pulse,
          scale * pulse,
          scale * pulse
        );
      }
      
      meshRef.current.position.lerp(
        new THREE.Vector3(position[0], position[1], position[2]),
        0.1
      );
    }
    
    if (glowRef.current) {
      glowRef.current.scale.lerp(
        new THREE.Vector3(scale * 1.5, scale * 1.5, scale * 1.5),
        0.1
      );
      glowRef.current.position.lerp(
        new THREE.Vector3(position[0], position[1], position[2]),
        0.1
      );
    }
  });
  
  const handlePointerOver = (e) => {
    e.stopPropagation();
    setHovered(true);
    document.body.style.cursor = 'pointer';
  };
  
  const handlePointerOut = (e) => {
    e.stopPropagation();
    setHovered(false);
    document.body.style.cursor = 'auto';
  };
  
  const handleClick = (e) => {
    e.stopPropagation();
    onSelect(data.id, neighbors);
  };
  
  return (
    <group>
      <mesh
        ref={glowRef}
        onPointerOver={handlePointerOver}
        onPointerOut={handlePointerOut}
        onClick={handleClick}
      >
        <sphereGeometry args={[1, 16, 16]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={isSelected || hovered ? 0.3 : 0.1}
        />
      </mesh>
      
      <mesh
        ref={meshRef}
        onPointerOver={handlePointerOver}
        onPointerOut={handlePointerOut}
        onClick={handleClick}
      >
        <sphereGeometry args={[1, 32, 32]} />
        <meshStandardMaterial
          color={color}
          metalness={0.3}
          roughness={0.5}
          emissive={color}
          emissiveIntensity={isSelected ? 0.5 : hovered ? 0.3 : 0.1}
        />
      </mesh>
      
      {(isSelected || hovered) && showLabels && (
        <Html
          position={[position[0], position[1] + 0.5, position[2]]}
          center
          distanceFactor={8}
        >
          <div className={`px-2 py-1 rounded text-xs font-medium whitespace-nowrap ${
            isSelected ? 'bg-primary-600 text-white' : 'bg-slate-800/90 text-slate-200'
          }`}>
            {data.name || data.id}
          </div>
        </Html>
      )}
    </group>
  );
}

function Edge({ start, end, weight = 1, isHighlighted, isHiddenRelation }) {
  const lineRef = useRef();
  
  const opacity = isHighlighted ? 0.8 : isHiddenRelation ? 0.5 : 0.15;
  const lineWidth = isHighlighted ? 3 : isHiddenRelation ? 2 : 1;
  const color = isHiddenRelation ? '#f59e0b' : '#475569';
  
  return (
    <Line
      ref={lineRef}
      points={[
        [start[0], start[1], start[2]],
        [end[0], end[1], end[2]]
      ]}
      color={color}
      lineWidth={lineWidth}
      transparent
      opacity={opacity}
      dashed={isHiddenRelation}
      dashSize={0.1}
      gapSize={0.05}
    />
  );
}

function ForceGraph({ 
  nodes, 
  edges, 
  selectedNode, 
  onSelectNode, 
  hiddenRelations = [],
  showLabels 
}) {
  const [positions, setPositions] = useState({});
  const forcesRef = useRef({
    position: new Map(),
    velocity: new Map()
  });
  const animatingRef = useRef(true);
  
  const nodeMap = useMemo(() => {
    const map = new Map();
    nodes.forEach(node => {
      map.set(node.id, node);
    });
    return map;
  }, [nodes]);
  
  const neighborMap = useMemo(() => {
    const map = new Map();
    nodes.forEach(node => {
      map.set(node.id, []);
    });
    edges.forEach(edge => {
      const sourceNeighbors = map.get(edge.source) || [];
      const targetNeighbors = map.get(edge.target) || [];
      
      if (!sourceNeighbors.includes(edge.target)) {
        sourceNeighbors.push(edge.target);
      }
      if (!targetNeighbors.includes(edge.source)) {
        targetNeighbors.push(edge.source);
      }
      
      map.set(edge.source, sourceNeighbors);
      map.set(edge.target, targetNeighbors);
    });
    return map;
  }, [nodes, edges]);
  
  const hiddenRelationMap = useMemo(() => {
    const map = new Map();
    hiddenRelations.forEach(rel => {
      const key = `${rel.model1_id}-${rel.model2_id}`;
      const reverseKey = `${rel.model2_id}-${rel.model1_id}`;
      map.set(key, rel);
      map.set(reverseKey, rel);
    });
    return map;
  }, [hiddenRelations]);
  
  useEffect(() => {
    const initialPositions = {};
    const radius = Math.min(8, nodes.length * 0.5);
    
    nodes.forEach((node, i) => {
      const phi = Math.acos(-1 + (2 * i) / nodes.length);
      const theta = Math.sqrt(nodes.length * Math.PI) * phi;
      
      initialPositions[node.id] = {
        x: radius * Math.cos(theta) * Math.sin(phi),
        y: radius * Math.sin(theta) * Math.sin(phi),
        z: radius * Math.cos(phi)
      };
    });
    
    setPositions(initialPositions);
    
    nodes.forEach(node => {
      forcesRef.current.position.set(node.id, { ...initialPositions[node.id] });
      forcesRef.current.velocity.set(node.id, { x: 0, y: 0, z: 0 });
    });
    
    animatingRef.current = true;
  }, [nodes]);
  
  useFrame(() => {
    if (!animatingRef.current || nodes.length === 0) return;
    
    const { position, velocity } = forcesRef.current;
    const damping = 0.92;
    const repulsionStrength = 0.8;
    const attractionStrength = 0.003;
    const centerStrength = 0.002;
    
    nodeMap.forEach((_, i) => {
      const posI = position.get(i);
      let fx = 0, fy = 0, fz = 0;
      
      nodeMap.forEach((_, j) => {
        if (i === j) return;
        const posJ = position.get(j);
        if (!posJ) return;
        
        const dx = posI.x - posJ.x;
        const dy = posI.y - posJ.y;
        const dz = posI.z - posJ.z;
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) || 0.1;
        
        const force = repulsionStrength / (dist * dist);
        fx += (dx / dist) * force;
        fy += (dy / dist) * force;
        fz += (dz / dist) * force;
      });
      
      const neighbors = neighborMap.get(i) || [];
      neighbors.forEach(j => {
        const posJ = position.get(j);
        if (!posJ) return;
        
        const dx = posJ.x - posI.x;
        const dy = posJ.y - posI.y;
        const dz = posJ.z - posI.z;
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) || 0.1;
        
        const force = dist * attractionStrength;
        fx += (dx / dist) * force;
        fy += (dy / dist) * force;
        fz += (dz / dist) * force;
      });
      
      fx += -posI.x * centerStrength;
      fy += -posI.y * centerStrength;
      fz += -posI.z * centerStrength;
      
      const vel = velocity.get(i) || { x: 0, y: 0, z: 0 };
      vel.x = (vel.x + fx) * damping;
      vel.y = (vel.y + fy) * damping;
      vel.z = (vel.z + fz) * damping;
      
      posI.x += vel.x;
      posI.y += vel.y;
      posI.z += vel.z;
      
      position.set(i, posI);
      velocity.set(i, vel);
    });
    
    setPositions(prev => {
      const newPositions = { ...prev };
      nodeMap.forEach((_, id) => {
        const pos = position.get(id);
        if (pos) {
          newPositions[id] = { ...pos };
        }
      });
      return newPositions;
    });
  });
  
  const selectedNeighbors = useMemo(() => {
    if (!selectedNode) return new Set();
    const neighbors = neighborMap.get(selectedNode) || [];
    return new Set([selectedNode, ...neighbors]);
  }, [selectedNode, neighborMap]);
  
  const renderEdges = useMemo(() => {
    const edgeComponents = [];
    
    edges.forEach((edge, i) => {
      const posSource = positions[edge.source];
      const posTarget = positions[edge.target];
      
      if (!posSource || !posTarget) return;
      
      const isHighlighted = selectedNode && 
        selectedNeighbors.has(edge.source) && 
        selectedNeighbors.has(edge.target);
      
      const isHidden = hiddenRelationMap.has(`${edge.source}-${edge.target}`);
      
      edgeComponents.push(
        <Edge
          key={`edge-${i}`}
          start={[posSource.x, posSource.y, posSource.z]}
          end={[posTarget.x, posTarget.y, posTarget.z]}
          weight={edge.weight}
          isHighlighted={isHighlighted}
          isHiddenRelation={isHidden}
        />
      );
    });
    
    hiddenRelations.forEach((rel, i) => {
      const pos1 = positions[rel.model1_id];
      const pos2 = positions[rel.model2_id];
      
      if (!pos1 || !pos2) return;
      
      const hasDirectEdge = edges.some(e => 
        (e.source === rel.model1_id && e.target === rel.model2_id) ||
        (e.source === rel.model2_id && e.target === rel.model1_id)
      );
      
      if (hasDirectEdge) return;
      
      edgeComponents.push(
        <Edge
          key={`hidden-${i}`}
          start={[pos1.x, pos1.y, pos1.z]}
          end={[pos2.x, pos2.y, pos2.z]}
          weight={rel.score}
          isHighlighted={false}
          isHiddenRelation={true}
        />
      );
    });
    
    return edgeComponents;
  }, [edges, positions, selectedNode, selectedNeighbors, hiddenRelationMap, hiddenRelations]);
  
  const renderNodes = useMemo(() => {
    return nodes.map(node => {
      const pos = positions[node.id];
      if (!pos) return null;
      
      const isHiddenNode = hiddenRelations.some(rel => 
        rel.model1_id === node.id || rel.model2_id === node.id
      );
      
      return (
        <Node
          key={node.id}
          position={[pos.x, pos.y, pos.z]}
          data={node}
          isSelected={selectedNode === node.id}
          onSelect={onSelectNode}
          isPulsing={isHiddenNode}
          neighbors={neighborMap.get(node.id) || []}
          showLabels={showLabels}
        />
      );
    });
  }, [nodes, positions, selectedNode, onSelectNode, neighborMap, hiddenRelations, showLabels]);
  
  return (
    <group>
      {renderEdges}
      {renderNodes}
    </group>
  );
}

export default function Network3D({ 
  graphData, 
  hiddenRelations = [],
  selectedNode,
  onSelectNode,
  showLabels = true 
}) {
  const { nodes = [], edges = [] } = graphData || {};
  
  return (
    <Canvas
      camera={{ position: [0, 0, 12], fov: 50 }}
      gl={{ antialias: true }}
      style={{ background: 'transparent' }}
    >
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={1} />
      <pointLight position={[-10, -10, -10]} intensity={0.5} color="#475569" />
      
      <ForceGraph
        nodes={nodes}
        edges={edges}
        selectedNode={selectedNode}
        onSelectNode={onSelectNode}
        hiddenRelations={hiddenRelations}
        showLabels={showLabels}
      />
      
      <OrbitControls
        enableDamping
        dampingFactor={0.05}
        minDistance={5}
        maxDistance={30}
      />
    </Canvas>
  );
}
