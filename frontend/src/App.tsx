import { useState, type FormEvent } from 'react';
import './App.css';

function App() {
  const [blogUrl, setBlogUrl] = useState('');

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!blogUrl.trim()) return;

    try {
      const response = await fetch('/api/health');

      if (!response.ok) {
        throw new Error('서버 응답 오류');
      }

      const data = await response.json();

      console.log('서버 응답:', data);
      console.log('입력한 블로그 URL:', blogUrl);

    } catch (error) {
      console.error('서버 연결 실패:', error);
    }
  };

  return (
    <main className="app">
      <div className="container">
        <span className="badge">BLOG TO SHORTS</span>

        <h1>블로그를 영상으로</h1>

        <p className="description">
          네이버 블로그 링크를 입력하면
          <br />
          쇼츠 영상으로 만들어 드립니다.
        </p>

        <form className="url-form" onSubmit={handleSubmit}>
          <input
            type="url"
            value={blogUrl}
            onChange={(e) => setBlogUrl(e.target.value)}
            placeholder="네이버 블로그 URL을 입력하세요"
            aria-label="네이버 블로그 URL"
            required
          />

          <button type="submit">
            시작하기 →
          </button>
        </form>
      </div>
    </main>
  );
}

export default App;