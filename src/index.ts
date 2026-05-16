import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json({ limit: '10mb' }));

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/api/info', (_req, res) => {
  res.json({
    name: '公众号专家',
    version: '0.1.0',
    mode: process.env.NODE_ENV,
  });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`公众号专家 API 运行在 http://0.0.0.0:${PORT}`);
});
