/**
 * 统一的样式预览示例内容
 * 适用于所有8套预设样式
 */

export interface Question {
  number: string;
  text: string;
  options: string[];
}

export interface SampleContent {
  title: string;
  subtitle2: string;
  questions: Question[];
  subtitle3: string;
  body: string;
  body2: string;
}

/**
 * 示例内容
 * 设计原则：
 * 1. 简短精炼，不会让预览区域过长
 * 2. 包含所有关键元素：标题、题号、选项、正文
 * 3. 真实的英语教学资料片段
 * 4. 适合所有学段（小学到高中）
 */
export const SAMPLE_CONTENT: SampleContent = {
  title: 'Unit 1 Friendship',
  subtitle2: '一、根据句意及首字母补全单词',
  questions: [
    {
      number: '1',
      text: 'She is very f_____. She has many friends.',
      options: ['A. friendly', 'B. friend', 'C. friends'],
    },
    {
      number: '2',
      text: 'They often s____ books after school.',
      options: ['A. see', 'B. saw', 'C. share'],
    },
    {
      number: '3',
      text: 'My best friend is very h_____. He helps others.',
      options: ['A. happy', 'B. help', 'C. helpful'],
    },
  ],
  subtitle3: '二、阅读理解',
  body: 'My best friend is Tom. He is tall and strong. He likes playing basketball and reading books. We often go to the library together on weekends. He is always ready to help others.',
  body2: 'Last Sunday, we went to the park. We played games and had a picnic. We were very happy that day. I think friendship is very important in our life.',
};
