import { create2D, ref, Vector2 } from "@motion-canvas/core";
import { Rect, Text, Group } from "@motion-canvas/2d";

// Colors
const AMBER = "#D97706";
const BLUE = "#2563EB";
const BG = "#0F0F0F";
const TEXT = "#E5E5E5";
const SUBTLE = "#9CA3AF";

export const diagnosticMatrix = create2D(({ duration }) => {
  return (
    <Group
      fill={TEXT}
      fontFamily="Menlo, monospace"
      fontSize={28}
    >
      <Rect
        size={[500, 300]}
        fill="transparent"
        stroke={SUBTLE}
        strokeWidth={1}
      />

      {/* Headers */}
      <Text
        text="Regret"
        position={[-60, -90]}
        fill={SUBTLE}
      />
      <Text
        text="No regret"
        position={[120, -90]}
        fill={SUBTLE}
      />
      <Text
        text="Gap present"
        position={[-260, -30]}
        fill={SUBTLE}
      />
      <Text
        text="No gap"
        position={[-260, 40]}
        fill={SUBTLE}
      />

      {/* Cells - appear sequentially */}
      <Group position={[-60, -30]}>
        <Rect size={[150, 60]} fill={AMBER} opacity={0} />
        <Text text="TP: 0" fill={BG} />
        <Group
          ref={cellTP}
          appearance={{ duration: 0.4 }}
          style={{ opacity: 0 }}
        />
      </Group>

      <Group position={[120, -30]}>
        <Rect size={[150, 60]} fill={BLUE} opacity={0} />
        <Text text="FA: 1" fill={BG} />
        <Group ref={cellFA} appearance={{ duration: 0.4 }} style={{ opacity: 0 }} />
      </Group>

      <Group position={[-60, 40]}>
        <Rect size={[150, 60]} fill={AMBER} opacity={0} />
        <Text text="FR: 1" fill={BG} />
        <Group ref={cellFR} appearance={{ duration: 0.4 }} style={{ opacity: 0 }} />
      </Group>

      <Group position={[120, 40]}>
        <Rect size={[150, 60]} fill={BLUE} opacity={0} />
        <Text text="TN: 7" fill={BG} />
        <Group ref={cellTN} appearance={{ duration: 0.4 }} style={{ opacity: 0 }} />
      </Group>
    </Group>
  );
});

export const headlineNumbers = create2D(({ duration }) => {
  return (
    <Group fill={TEXT} fontFamily="Menlo, monospace" fontSize={40}>
      <Text
        text="Judge accuracy: 77.8%"
        position={[0, -60]}
        appearance={{ duration: 0.5 }}
        style={{ opacity: 0 }}
      />
      <Text
        text="Always-negative baseline: 88.9%"
        position={[0, 10]}
        fill={SUBTLE}
        appearance={{ duration: 0.5 }}
        delay={0.5}
        style={{ opacity: 0 }}
      />
      <Text
        text="Sensitivity: 0.0%"
        position={[0, 80]}
        fill={AMBER}
        appearance={{ duration: 0.5 }}
        delay={1.0}
        style={{ opacity: 0 }}
      />
    </Group>
  );
});

export const caseCards = create2D(({ duration }) => {
  return (
    <Group fill={TEXT} fontFamily="Menlo, monospace">
      {/* Left card - software_deployment_b */}
      <Group position={[-300, 0]}>
        <Rect size={[500, 200]} fill="#1a1a1a" stroke={AMBER} strokeWidth={2} />
        <Text text="software_deployment_b" position={[-220, -60]} fill={AMBER} fontSize={20} />
        <Text text="Gap: 0" position={[-220, -10]} />
        <Text text="Regret: 1,200" position={[-220, 30]} />
        <Text text="FALSE REASSURANCE" position={[-220, 70]} fill={AMBER} fontSize={16} />
        <Group ref={leftCard} appearance={{ duration: 0.6 }} style={{ opacity: 0 }} />
      </Group>

      {/* Right card - cybersecurity_investment_j */}
      <Group position={[300, 0]}>
        <Rect size={[500, 200]} fill="#1a1a1a" stroke={BLUE} strokeWidth={2} />
        <Text text="cybersecurity_investment_j" position={[220, -60]} fill={BLUE} fontSize={20} />
        <Text text="Gap: 2" position={[220, -10]} />
        <Text text="Regret: 0" position={[220, 30]} />
        <Text text="FALSE ALARM" position={[220, 70]} fill={BLUE} fontSize={16} />
        <Group ref={rightCard} appearance={{ duration: 0.6 }} style={{ opacity: 0 }} />
      </Group>
    </Group>
  );
});

export const titleReveal = create2D(({ duration }) => {
  return (
    <Group fill={TEXT} fontFamily="Menlo, monospace">
      <Text
        text="GUSSET"
        position={[0, -40]}
        fontSize={72}
        appearance={{ duration: 0.6 }}
        style={{ opacity: 0 }}
      />
      <Text
        text="Does an epistemic gap predict decision regret?"
        position={[0, 60]}
        fontSize={24}
        fill={SUBTLE}
        appearance={{ duration: 0.6 }}
        delay={0.6}
        style={{ opacity: 0 }}
      />
    </Group>
  );
});

const cellTP = ref<Group>();
const cellFA = ref<Group>();
const cellFR = ref<Group>();
const cellTN = ref<Group>();
const leftCard = ref<Group>();
const rightCard = ref<Group>();
