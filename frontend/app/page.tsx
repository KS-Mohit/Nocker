"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [status, setStatus] = useState<string>("checking...");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    fetch("http://localhost:8000/health")
      .then((res) => res.json())
      .then((data) => setStatus(data.status))
      .catch((err) => {
        setStatus("error");
        setError(err.message);
      });
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24 bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="text-center space-y-6">
        <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          Job Application Agent
        </h1>
        <p className="text-xl text-gray-700">
          Automate your job applications with AI
        </p>

        <div className="bg-white p-6 rounded-lg shadow-lg">
          <p className="text-lg text-gray-600 mb-2">
            Backend Status:{" "}
            <span
              className={
                status === "healthy"
                  ? "text-green-600 font-semibold"
                  : "text-red-600 font-semibold"
              }
            >
              {status}
            </span>
          </p>
          {error && <p className="text-sm text-red-500">Error: {error}</p>}
        </div>

        <div className="flex gap-4 justify-center mt-8">
          
            <a href="http://localhost:8000/api/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition shadow-md hover:shadow-lg"
          >
            API Documentation
          </a>
          <button
            disabled
            className="px-6 py-3 bg-gray-400 text-white rounded-lg cursor-not-allowed opacity-50"
          >
            Dashboard (Coming Soon)
          </button>
        </div>

        <div className="mt-8 text-sm text-gray-500">
          <p>Ready to build amazing features!</p>
        </div>
      </div>
    </main>
  );
}