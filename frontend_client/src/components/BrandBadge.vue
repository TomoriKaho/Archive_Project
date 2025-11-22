<template>
  <div class="brand-badge">
    <span class="brand-badge__orb" aria-hidden="true"></span>
    <div class="brand-badge__text">
      <span class="brand-badge__title">Pacific Silk Road</span>
      <span class="brand-badge__subtitle">太平洋丝绸之路</span>
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped lang="scss">
.brand-badge {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.85rem;
  padding: 0.9rem 1.2rem;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.92), rgba(255, 255, 255, 0.78));
  box-shadow: 0 20px 38px rgba(27, 43, 102, 0.15);
  backdrop-filter: blur(10px);
  overflow: hidden;
}

.brand-badge__orb {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: conic-gradient(from 140deg, #2c9ecb, #7b5bff, #ff7eb6, #2c9ecb);
  filter: blur(0.2px) drop-shadow(0 10px 18px rgba(43, 90, 170, 0.35));
  animation: brandPulse 8s ease-in-out infinite;
}

.brand-badge__text {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  line-height: 1.1;
}

.brand-badge__title {
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: #1c2754;
  text-transform: uppercase;
}

.brand-badge__subtitle {
  font-size: 0.95rem;
  font-weight: 600;
  color: #57689a;
  letter-spacing: 0.08em;
}

@keyframes brandPulse {
  0% {
    transform: rotate(0deg) scale(1);
  }
  50% {
    transform: rotate(8deg) scale(1.04);
  }
  100% {
    transform: rotate(0deg) scale(1);
  }
}

@media (max-width: 640px) {
  .brand-badge {
    gap: 0.65rem;
    padding: 0.75rem 1rem;
  }

  .brand-badge__orb {
    width: 38px;
    height: 38px;
  }

  .brand-badge__title {
    font-size: 0.95rem;
  }

  .brand-badge__subtitle {
    font-size: 0.85rem;
  }
}
</style>
