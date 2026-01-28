import React, { useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './Home.css';

/**
 * 首页组件
 * @description 展示品牌信息和快速入口，包含粒子动画背景效果
 */
function Home() {
  const navigate = useNavigate();
  const canvasRef = useRef(null);
  const animationRef = useRef(null);

  /**
   * 初始化粒子动画
   * 创建粒子系统并绘制连线效果
   */
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let particles = [];

    // 设置画布尺寸
    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // 粒子类
    class Particle {
      constructor() {
        this.reset();
      }

      reset() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height;
        this.size = Math.random() * 2 + 1;
        this.speedX = (Math.random() - 0.5) * 0.8;
        this.speedY = (Math.random() - 0.5) * 0.8;
        this.opacity = Math.random() * 0.5 + 0.2;
        // 科技感颜色：蓝色、紫色、青色
        const colors = [
          'rgba(0, 113, 227,',   // 品牌蓝
          'rgba(118, 75, 162,',  // 紫色
          'rgba(0, 242, 254,',   // 青色
          'rgba(102, 126, 234,'  // 淡紫蓝
        ];
        this.color = colors[Math.floor(Math.random() * colors.length)];
      }

      update() {
        this.x += this.speedX;
        this.y += this.speedY;

        // 边界检测
        if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
        if (this.y < 0 || this.y > canvas.height) this.speedY *= -1;
      }

      draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fillStyle = this.color + this.opacity + ')';
        ctx.fill();
      }
    }

    // 创建粒子
    const particleCount = Math.min(120, Math.floor((canvas.width * canvas.height) / 12000));
    for (let i = 0; i < particleCount; i++) {
      particles.push(new Particle());
    }

    // 绘制粒子连线
    const drawLines = () => {
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const distance = Math.sqrt(dx * dx + dy * dy);

          if (distance < 150) {
            const opacity = (1 - distance / 150) * 0.25;
            ctx.beginPath();
            ctx.strokeStyle = `rgba(0, 113, 227, ${opacity})`;
            ctx.lineWidth = 0.5;
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.stroke();
          }
        }
      }
    };

    // 动画循环
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particles.forEach(particle => {
        particle.update();
        particle.draw();
      });

      drawLines();
      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    // 清理函数
    return () => {
      window.removeEventListener('resize', resizeCanvas);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, []);

  return (
    <div className="home-container">
      {/* 粒子背景画布 */}
      <canvas ref={canvasRef} className="particle-canvas" />
      
      {/* 装饰性光晕 */}
      <div className="glow-orb glow-orb-1" />
      <div className="glow-orb glow-orb-2" />
      <div className="glow-orb glow-orb-3" />

      {/* 主内容区域 */}
      <div className="home-content">
        <div className="text-center max-w-2xl px-4">
          {/* 主标题 - 渐变流动效果 */}
          <h1 className="home-title">
            我是报价侠
          </h1>
          
          {/* 副标题 */}
          <h2 className="home-subtitle">
            服务于云前线的智能报价助手
          </h2>
          
          {/* 主入口按钮 */}
          <div className="flex justify-center gap-4">
            <button
              onClick={() => navigate('/quote/step1')}
              className="home-button home-button-primary"
            >
              <span className="button-glow" />
              <span className="relative z-10 flex items-center gap-2">
                <span>📝</span> 标准报价
              </span>
            </button>
            
            {/* 极速报价入口 */}
            <button
              onClick={() => navigate('/express-quote')}
              className="home-button home-button-express"
            >
              <span className="button-glow" />
              <span className="relative z-10 flex items-center gap-2">
                <span>⚡</span> 极速报价
              </span>
            </button>
          </div>
          
          {/* AI 助手提示 */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-400">
              💡 点击右下角 <span className="text-blue-400">AI 助手</span> 可获得智能报价支持
            </p>
          </div>
          
          {/* 底部信息 */}
          <div className="home-footer">
            <p className="mt-2">提供快速、准确、可追溯的报价方案</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Home;
