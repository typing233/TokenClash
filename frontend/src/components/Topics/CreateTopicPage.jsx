import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { topicsApi } from '../../services/api';
import { ArrowLeft, Send } from 'lucide-react';

const CATEGORIES = [
  '科技', '生活', '教育', '娱乐', '商业', '社会', '综合'
];

const CreateTopicPage = () => {
  const navigate = useNavigate();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('综合');
  const [tags, setTags] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!title.trim()) {
      setError('请输入话题标题');
      return;
    }
    
    if (title.trim().length < 5) {
      setError('话题标题至少需要5个字符');
      return;
    }
    
    try {
      setSubmitting(true);
      setError(null);
      
      // 解析标签
      const tagArray = tags
        .split(',')
        .map(t => t.trim())
        .filter(t => t.length > 0);
      
      await topicsApi.create({
        title: title.trim(),
        description: description.trim() || undefined,
        category: category,
        tags: tagArray.length > 0 ? tagArray : undefined,
        is_auto_generated: false
      });
      
      // 返回话题列表
      navigate('/topics');
      
    } catch (err) {
      console.error('Failed to create topic:', err);
      setError(err.response?.data?.detail || '创建话题失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-4 md:p-6">
      {/* 页面标题 */}
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={() => navigate(-1)}
          className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-slate-400" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-slate-100">发起新话题</h1>
          <p className="text-slate-400 mt-1">创建一个话题，让AI展开辩论</p>
        </div>
      </div>
      
      {/* 表单 */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* 话题标题 */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            话题标题 <span className="text-red-400">*</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="例如：人工智能是否会取代人类工作？"
            className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 transition-colors"
          />
          <p className="text-xs text-slate-500 mt-1">
            建议使用"是否"、"应该"、"更好"等对比式问题
          </p>
        </div>
        
        {/* 话题描述 */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            话题描述
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="详细描述这个话题的背景和争议点..."
            rows={4}
            className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 transition-colors resize-none"
          />
        </div>
        
        {/* 分类 */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            分类
          </label>
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map(cat => (
              <button
                key={cat}
                type="button"
                onClick={() => setCategory(cat)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  category === cat
                    ? 'bg-primary-600 text-white'
                    : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
        
        {/* 标签 */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            标签
          </label>
          <input
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="多个标签用逗号分隔，例如：AI, 未来, 职业"
            className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 transition-colors"
          />
          <p className="text-xs text-slate-500 mt-1">
            多个标签用英文逗号分隔
          </p>
        </div>
        
        {/* 错误提示 */}
        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm">
            {error}
          </div>
        )}
        
        {/* 提交按钮 */}
        <div className="flex justify-end gap-4">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="px-6 py-3 text-slate-400 hover:text-slate-200 font-medium transition-colors"
          >
            取消
          </button>
          <button
            type="submit"
            disabled={submitting}
            className={`inline-flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
              submitting
                ? 'bg-slate-600 cursor-not-allowed text-slate-400'
                : 'bg-primary-600 hover:bg-primary-500 text-white'
            }`}
          >
            {submitting ? (
              <>
                <div className="loading-spinner w-5 h-5 border-slate-400 border-t-primary-500" />
                <span>创建中...</span>
              </>
            ) : (
              <>
                <Send className="w-5 h-5" />
                <span>创建话题</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default CreateTopicPage;
