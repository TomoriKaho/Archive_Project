export const messages = {
  zh: {
    app: {
      name: '人工智能档案库',
      switchToEnglish: 'Switch to English',
      switchToChinese: 'Switch to Chinese'
    },
    roles: {
      admin: '管理员',
      member: '成员'
    },
    navigation: {
      dashboard: '仪表盘',
      documents: '文档管理',
      chat: '开始对话',
      domains: '域管理',
      users: '用户管理',
      profile: '个人资料',
      logout: '退出登录'
    },
    common: {
      cancel: '取消',
      saving: '正在保存…',
      search: '搜索',
      edit: '编辑',
      delete: '删除',
      view: '查看',
      previous: '上一页',
      next: '下一页',
      close: '关闭',
      save: '保存',
      deleting: '正在删除…',
      saveChanges: '保存更改',
      back: '返回'
    },
    auth: {
      errors: {
        missingToken: '服务器未返回访问令牌。'
      },
      login: {
        title: '欢迎回来',
        subtitle: '登录以继续管理档案。',
        emailLabel: '邮箱',
        emailPlaceholder: 'ni@example.com',
        passwordLabel: '密码',
        passwordPlaceholder: '••••••••',
        submit: '登录',
        submitting: '正在登录…',
        needAccount: '还没有账号？',
        registerLink: '注册',
        validation: {
          emailRequired: '请输入邮箱地址。',
          emailInvalid: '请输入有效的邮箱地址。',
          passwordRequired: '请输入密码。',
          passwordWeak: '至少使用 8 个字符，并包含数字与大写字母。'
        }
      },
      register: {
        title: '创建账号',
        subtitle: '加入归档智能，轻松管理知识。',
        nameLabel: '姓名',
        namePlaceholder: '例如：Ada Lovelace',
        emailLabel: '邮箱',
        emailPlaceholder: 'ni@example.com',
        passwordLabel: '密码',
        passwordPlaceholder: '安全密码',
        confirmLabel: '确认密码',
        confirmPlaceholder: '再次输入密码',
        submit: '创建账号',
        submitting: '正在创建账号…',
        haveAccount: '已经有账号？',
        loginLink: '立即登录',
        validation: {
          nameRequired: '请输入姓名。',
          nameTooLong: '姓名长度不能超过 30 个字符。',
          emailRequired: '请输入邮箱地址。',
          emailInvalid: '请输入有效的邮箱地址。',
          passwordRequired: '请输入密码。',
          passwordWeak: '至少使用 8 个字符，并包含数字与大写字母。',
          passwordMismatch: '两次输入的密码不一致。'
        }
      },
      toast: {
        loginSuccess: '登录成功。',
        loginError: '登录失败，请检查邮箱或密码是否正确。',
        registerSuccess: '账号已创建，请登录。',
        registerError: '无法注册，请稍后重试。',
        registerEmailTaken: '邮箱已注册，请使用其他邮箱。',
        logout: '您已退出登录。'
      }
    },
    dashboard: {
      greetingNamed: '你好，{name}',
      greetingUnnamed: '你好，探索者',
      subtitle: '以下是知识库的最新动态。',
      profile: {
        title: '个人信息',
        name: '姓名',
        email: '邮箱',
        role: '角色'
      },
      recentActivity: {
        title: '最近活动',
        empty: '暂无最近的文档。',
        updated: '更新于 {date}'
      },
      quickLinks: {
        title: '快捷入口',
        documents: '管理文档',
        chat: '开始对话',
        domains: '域管理',
        profile: '个人资料',
        users: '用户管理'
      }
    },
    profile: {
      title: '个人资料',
      subtitle: '更新你的账户信息。',
      form: {
        nameLabel: '姓名',
        namePlaceholder: '如：张伟',
        emailLabel: '邮箱',
        emailPlaceholder: 'name@example.com',
        passwordLabel: '新密码',
        passwordPlaceholder: '填写以更新密码',
        confirmLabel: '确认密码',
        confirmPlaceholder: '再次输入新密码',
        passwordHint: '留空则保持当前密码。',
        save: '保存更改',
        saving: '正在保存…'
      },
      validation: {
        emailRequired: '请输入邮箱地址。',
        emailInvalid: '请输入有效的邮箱地址。',
        passwordLength: '密码至少需要 8 个字符。',
        passwordMismatch: '两次输入的密码不一致。'
      },
      toast: {
        updateSuccess: '个人资料已更新。',
        updateError: '更新个人资料失败。'
      }
    },
    documents: {
      title: '文档',
      subtitle: '管理知识资产并确保与向量存储同步。',
      actions: {
        new: '新建文档',
        create: '创建'
      },
      search: {
        label: '搜索',
        placeholder: '搜索文档',
        clearAria: '清除搜索条件'
      },
      filters: {
        domain: {
          label: '域',
          all: '全部域'
        }
      },
      modal: {
        createTitle: '新建文档'
      },
      tabs: {
        text: '纯文本',
        csv: 'CSV 上传'
      },
      form: {
        domainLabel: '域',
        domainPlaceholder: '请选择域',
        titleLabel: '标题',
        titlePlaceholder: '文档标题',
        contentLabel: '内容',
        contentPlaceholder: '在此粘贴内容'
      },
      csv: {
        dropHint: '拖放 CSV 文件至此，或点击选择。',
        selectFile: '选择文件',
        selectedFile: '已选择：{name}'
      },
      validation: {
        domainRequired: '请选择域。',
        titleRequired: '标题为必填项。',
        contentRequired: '内容不能为空。',
        csvRequired: '请选择要上传的 CSV 文件。',
        csvType: '仅支持 CSV 文件。'
      },
      table: {
        columns: {
          name: '名称',
          domain: '域',
          created: '创建时间',
          updated: '更新时间'
        },
        empty: '未找到文档。',
        progress: {
          summary: '导入进度：{status} · {percent}%',
          summaryNoStatus: '导入进度：{percent}%',
          failed: '导入进度：导入失败',
          status: {
            pending: '等待中',
            queued: '排队中',
            processing: '进行中',
            completed: '已完成',
            cancelled: '已取消',
            paused: '已暂停'
          }
        },
        actions: {
          pause: '暂停导入',
          resume: '继续导入',
          cancelUpload: '取消上传',
          pausing: '暂停中…',
          resuming: '继续中…',
          cancelling: '取消中…',
          cancelConfirm: '确定要取消“{title}”的上传吗？该操作会删除已上传的内容。'
        }
      },
      unknownDomain: '域 #{id}',
      uploading: '正在上传…',
      toast: {
        loadError: '加载文档失败。',
        fetchError: '获取文档失败。',
        createSuccess: '文档创建成功。',
        createError: '创建文档失败。',
        uploadSuccess: '“{title}” 文档上传成功。',
        uploadError: '上传 CSV 失败。',
        contentError: '加载文档内容失败。',
        chunksError: '加载文档片段失败，将仅展示原文。',
        updateSuccess: '文档更新成功。',
        updateError: '更新文档失败。',
        deleteSuccess: '文档已删除。',
        deleteError: '删除文档失败。',
        cancelSuccess: '已取消向量导入。',
        cancelError: '取消向量导入失败。',
        pauseSuccess: '导入已暂停，可随时继续。',
        pauseError: '暂停导入失败。',
        resumeSuccess: '已重新开始导入。',
        resumeError: '恢复导入失败。',
        cancelUploadSuccess: '已取消上传并删除文档。',
        cancelUploadError: '取消上传失败。'
      }
    },
    documentDetail: {
      domainLabel: '域：{name}',
      meta: {
        created: '创建时间',
        updated: '更新时间',
        uuid: 'UUID',
        domainId: '域 ID'
      },
      content: {
        title: '文档内容',
        loading: '正在加载内容…',
        empty: '该文档暂无原始内容。',
        rangeLabel: '范围',
        total: '共 {total} {unit}',
        units: {
          rows: '行',
          lines: '行'
        }
      },
      csv: {
        autoHeader: '列 {index}'
      },
      chunks: {
        title: '内容片段',
        summary: '共存储 {count} 个片段。',
        currentRange: '当前查看 {range}。',
        rangeLabel: '范围',
        loading: '正在加载片段…',
        empty: '该文档尚未生成任何片段。',
        itemTitle: '片段 {index}',
        length: '长度 {count} 字符'
      },
      preview: {
        title: '单元格内容预览',
        meta: '第 {row} 行 · {header}'
      },
      edit: {
        title: '编辑文档',
        save: '保存更改'
      },
      delete: {
        title: '删除文档',
        message: '删除该文档将永久移除文档及其所有片段，此操作无法撤销。是否继续？',
        confirm: '删除文档'
      },
      loadingDocument: '正在加载文档…',
      loadError: '无法加载文档，请返回列表后重试。'
    },
    domains: {
      title: '域',
      subtitle: '管理用于文档导入的来源。',
      actions: {
        new: '新建域'
      },
      table: {
        name: '名称',
        description: '描述',
        created: '创建时间',
        updated: '更新时间'
      },
      empty: '未找到域。',
      form: {
        nameLabel: '名称',
        descriptionLabel: '描述',
        descriptionPlaceholder: '可选描述',
        hint: '域创建后默认启用。',
        validation: {
          nameRequired: '请输入域名称。'
        }
      },
      modal: {
        editTitle: '编辑域',
        newTitle: '新建域'
      },
      delete: {
        title: '删除域',
        message: '删除域将移除该域及其相关文档，此操作无法撤销。是否继续？',
        confirm: '删除域'
      },
      toast: {
        loadError: '加载域失败。',
        createSuccess: '域创建成功。',
        createError: '创建域失败。',
        duplicateName: '该域名称已存在，请更换其他名称。',
        updateSuccess: '域更新成功。',
        updateError: '更新域失败。',
        deleteSuccess: '域已删除。',
        deleteError: '删除域失败。'
      }
    },
    users: {
      title: '用户',
      subtitle: '管理角色、密码与访问权限。',
      empty: '未找到用户。',
      table: {
        name: '姓名',
        email: '邮箱',
        admin: '管理员',
        updated: '更新时间',
        created: '创建时间'
      },
      roles: {
        admin: '管理员',
        standard: '普通用户'
      },
      form: {
        nameLabel: '姓名',
        namePlaceholder: '姓名（可选）',
        nameTooLong: '姓名长度不能超过 30 个字符。',
        emailLabel: '邮箱',
        emailPlaceholder: 'ni@example.com',
        emailRequired: '请输入邮箱地址。',
        emailInvalid: '请输入有效的邮箱地址。',
        passwordLabel: '新密码',
        passwordPlaceholder: '留空则保持当前密码',
        passwordHint: '留空将保留当前密码。'
      },
      modal: {
        title: '编辑 {name}'
      },
      delete: {
        message: '删除该用户将立即移除其访问权限，此操作无法撤销。是否继续？',
        confirm: '删除用户',
        button: '删除用户'
      },
      toast: {
        loadError: '加载用户失败。',
        updateSuccess: '用户已更新。',
        updateError: '更新用户失败。',
        deleteSuccess: '用户已删除。',
        deleteError: '删除用户失败。'
      }
    },
    chat: {
      sidebar: {
        title: '会话',
        new: '新建',
        untitled: '未命名会话',
        editAria: '编辑会话',
        edit: '编辑'
      },
      filter: {
        manage: '管理域筛选',
        title: '域筛选',
        hint: '不选择任何域即表示搜索全部域。',
        clearSelection: '清除选择',
        apply: '应用',
        noConversation: '请选择会话以配置域筛选。',
        unavailable: '暂无法使用域筛选。',
        allDomains: '筛选：所有域',
        applied: '筛选：{domains}',
        separator: '、',
        unsaved: '已修改，应用后生效',
        status: {
          noConversation: '选择会话以管理域',
          count: '已选择 {count} 个域',
          all: '已选择所有域'
        }
      },
      messages: {
        empty: '暂无消息，请发送第一条消息。',
        you: '你',
        assistant: '助手',
        system: '系统提示',
        typing: '助手正在输入…'
      },
      composer: {
        placeholder: '输入消息并发送',
        send: '发送'
      },
      placeholder: {
        title: '尚未选择会话',
        instructions: '从列表中选择会话或新建一个会话开始交流。',
        empty: '创建新会话以开始聊天。'
      },
      new: {
        title: '新建会话',
        defaultTitle: '新会话',
        nameLabel: '会话标题（可选）',
        namePlaceholder: '可选，留空自动命名',
        promptLabel: '初始提示（可选）',
        promptPlaceholder: '可选的系统提示，例如指定助手角色',
        domainLabel: '域筛选（可选）',
        domainHint: '选择限定检索的域，留空表示包含全部域。',
        start: '开始会话',
        starting: '正在开始…',
        validation: {
          nameRequired: '请输入会话标题。'
        }
      },
      delete: {
        title: '删除会话',
        message: '确认删除该会话？此操作无法撤销，所有消息将被移除。',
        confirm: '删除会话'
      },
      edit: {
        title: '编辑会话',
        nameLabel: '会话标题',
        namePlaceholder: '可选，留空自动命名',
        deleteWarning: '删除此会话将移除全部消息，操作不可恢复，是否继续？'
      },
      errors: {
        notAuthenticated: '请先登录以创建会话。'
      },
      toast: {
        loadError: '无法加载会话。',
        messagesError: '无法加载消息。',
        createSuccess: '会话已创建。',
        createError: '无法创建会话。',
        sendError: '发送消息失败。',
        domainApplied: '已更新域筛选。',
        domainCleared: '已清除域筛选。',
        updateSuccess: '会话已更新。',
        updateError: '无法更新会话。',
        deleteError: '无法删除会话。',
        deleteSuccess: '会话已删除。',
        deleteMissing: '会话不存在，已从列表中移除。'
      }
    },
    notFound: {
      title: '页面未找到',
      description: '你访问的页面不存在。',
      backToDashboard: '返回仪表盘'
    },
    Profile: '个人资料'
  },
  en: {
    app: {
      name: 'Archive AI',
      switchToEnglish: '切换为英文',
      switchToChinese: '切换为中文'
    },
    roles: {
      admin: 'Admin',
      member: 'Member'
    },
    navigation: {
      dashboard: 'Dashboard',
      documents: 'Documents',
      chat: 'Chat',
      domains: 'Domains',
      users: 'Users',
      profile: 'Profile',
      logout: 'Log out'
    },
    common: {
      cancel: 'Cancel',
      saving: 'Saving…',
      search: 'Search',
      edit: 'Edit',
      delete: 'Delete',
      view: 'View',
      previous: 'Previous',
      next: 'Next',
      close: 'Close',
      save: 'Save',
      deleting: 'Deleting…',
      saveChanges: 'Save changes',
      back: 'Back'
    },
    auth: {
      errors: {
        missingToken: 'No access token received from the server.'
      },
      login: {
        title: 'Welcome back',
        subtitle: 'Sign in to continue managing your archives.',
        emailLabel: 'Email',
        emailPlaceholder: 'you@example.com',
        passwordLabel: 'Password',
        passwordPlaceholder: '••••••••',
        submit: 'Sign In',
        submitting: 'Signing in…',
        needAccount: 'Need an account?',
        registerLink: 'Register',
        validation: {
          emailRequired: 'Email is required.',
          emailInvalid: 'Enter a valid email address.',
          passwordRequired: 'Password is required.',
          passwordWeak: 'Use at least 8 characters with a number and uppercase letter.'
        }
      },
      register: {
        title: 'Create your account',
        subtitle: 'Join Archive AI to manage knowledge effortlessly.',
        nameLabel: 'Full name',
        namePlaceholder: 'Ada Lovelace',
        emailLabel: 'Email',
        emailPlaceholder: 'you@example.com',
        passwordLabel: 'Password',
        passwordPlaceholder: 'Strong password',
        confirmLabel: 'Confirm password',
        confirmPlaceholder: 'Re-enter password',
        submit: 'Create Account',
        submitting: 'Creating account…',
        haveAccount: 'Already have an account?',
        loginLink: 'Sign in',
        validation: {
          nameRequired: 'Name is required.',
          nameTooLong: 'Name must be 30 characters or fewer.',
          emailRequired: 'Email is required.',
          emailInvalid: 'Enter a valid email address.',
          passwordRequired: 'Password is required.',
          passwordWeak: 'Use at least 8 characters with a number and uppercase letter.',
          passwordMismatch: 'Passwords must match.'
        }
      },
      toast: {
        loginSuccess: 'Logged in successfully.',
        loginError: 'Unable to login. Please check your email or password.',
        registerSuccess: 'Account created. Please login.',
        registerError: 'Unable to register. Please try again.',
        registerEmailTaken: 'Email is already registered. Please sign in or use another email.',
        logout: 'You have been logged out.'
      }
    },
    dashboard: {
      greetingNamed: 'Hello, {name}',
      greetingUnnamed: 'Hello, Explorer',
      subtitle: "Here's what's happening with your knowledge base today.",
      profile: {
        title: 'Profile',
        name: 'Name',
        email: 'Email',
        role: 'Role'
      },
      recentActivity: {
        title: 'Recent Activity',
        empty: 'No recent documents.',
        updated: 'Updated {date}'
      },
      quickLinks: {
        title: 'Quick Links',
        documents: 'Manage Documents',
        chat: 'Start Conversation',
        domains: 'Manage Domains',
        profile: 'Your Profile',
        users: 'Manage Users'
      }
    },
    profile: {
      title: 'Profile',
      subtitle: 'Keep your account details up to date.',
      form: {
        nameLabel: 'Name',
        namePlaceholder: 'e.g. Ada Lovelace',
        emailLabel: 'Email',
        emailPlaceholder: 'name@example.com',
        passwordLabel: 'New Password',
        passwordPlaceholder: 'Enter a new password to update it',
        confirmLabel: 'Confirm Password',
        confirmPlaceholder: 'Re-enter the new password',
        passwordHint: 'Leave blank to keep your existing password.',
        save: 'Save Changes',
        saving: 'Saving…'
      },
      validation: {
        emailRequired: 'Please enter your email address.',
        emailInvalid: 'Enter a valid email address.',
        passwordLength: 'Password must be at least 8 characters long.',
        passwordMismatch: 'Passwords do not match.'
      },
      toast: {
        updateSuccess: 'Profile updated successfully.',
        updateError: 'Unable to update your profile.'
      }
    },
    documents: {
      title: 'Documents',
      subtitle: 'Manage your knowledge assets and keep them in sync with the vector store.',
      actions: {
        new: 'New Document',
        create: 'Create'
      },
      search: {
        label: 'Search',
        placeholder: 'Search documents',
        clearAria: 'Clear search filter'
      },
      filters: {
        domain: {
          label: 'Domain',
          all: 'All domains'
        }
      },
      modal: {
        createTitle: 'Create Document'
      },
      tabs: {
        text: 'Plain Text',
        csv: 'CSV Upload'
      },
      form: {
        domainLabel: 'Domain',
        domainPlaceholder: 'Select a domain',
        titleLabel: 'Title',
        titlePlaceholder: 'Document title',
        contentLabel: 'Content',
        contentPlaceholder: 'Paste your content here'
      },
      csv: {
        dropHint: 'Drag & drop your CSV here or click to browse.',
        selectFile: 'Select File',
        selectedFile: 'Selected: {name}'
      },
      validation: {
        domainRequired: 'Select a domain.',
        titleRequired: 'Title is required.',
        contentRequired: 'Content cannot be empty.',
        csvRequired: 'Select a CSV file to upload.',
        csvType: 'Only CSV files are allowed.'
      },
      table: {
        columns: {
          name: 'Name',
          domain: 'Domain',
          created: 'Created',
          updated: 'Updated'
        },
        empty: 'No documents found.',
        progress: {
          summary: 'Progress: {status} · {percent}%',
          summaryNoStatus: 'Progress: {percent}%',
          failed: 'Progress: failed',
          status: {
            pending: 'Waiting',
            queued: 'Queued',
            processing: 'In progress',
            completed: 'Completed',
            cancelled: 'Cancelled',
            paused: 'Paused'
          }
        },
        actions: {
          pause: 'Pause Import',
          resume: 'Resume Import',
          cancelUpload: 'Cancel Upload',
          pausing: 'Pausing…',
          resuming: 'Resuming…',
          cancelling: 'Cancelling…',
          cancelConfirm: 'Cancel upload for “{title}”? Progress will be lost.'
        }
      },
      unknownDomain: 'Domain #{id}',
      uploading: 'Uploading…',
      toast: {
        loadError: 'Failed to load documents.',
        fetchError: 'Unable to fetch document.',
        createSuccess: 'Document created successfully.',
        createError: 'Failed to create document.',
        uploadSuccess: '“{title}” uploaded successfully.',
        uploadError: 'Failed to upload CSV.',
        contentError: 'Failed to load document content.',
        chunksError: 'Unable to load document chunks; showing the original file only.',
        updateSuccess: 'Document updated successfully.',
        updateError: 'Failed to update document.',
        deleteSuccess: 'Document deleted.',
        deleteError: 'Failed to delete document.',
        cancelSuccess: 'Vector import cancelled.',
        cancelError: 'Failed to cancel vector import.',
        pauseSuccess: 'Import paused. You can resume later.',
        pauseError: 'Failed to pause import.',
        resumeSuccess: 'Import resumed.',
        resumeError: 'Failed to resume import.',
        cancelUploadSuccess: 'Upload cancelled and document removed.',
        cancelUploadError: 'Failed to cancel the upload.'
      }
    },
    documentDetail: {
      domainLabel: 'Domain: {name}',
      meta: {
        created: 'Created',
        updated: 'Updated',
        uuid: 'UUID',
        domainId: 'Domain ID'
      },
      content: {
        title: 'Document content',
        loading: 'Loading content…',
        empty: 'No original content is available for this document.',
        rangeLabel: 'Range',
        total: 'Total {total} {unit}',
        units: {
          rows: 'rows',
          lines: 'lines'
        }
      },
      csv: {
        autoHeader: 'Column {index}'
      },
      chunks: {
        title: 'Chunks',
        summary: 'Stored {count} chunk(s) for this document.',
        currentRange: 'Currently viewing {range}.',
        rangeLabel: 'Range',
        loading: 'Loading chunks…',
        empty: 'No chunks have been generated for this document yet.',
        itemTitle: 'Chunk {index}',
        length: '{count} characters'
      },
      preview: {
        title: 'Cell content preview',
        meta: 'Row {row} · {header}'
      },
      edit: {
        title: 'Edit Document',
        save: 'Save changes'
      },
      delete: {
        title: 'Delete Document',
        message: 'Deleting this document will remove it and all of its chunks permanently. This action cannot be undone. Do you want to continue?',
        confirm: 'Delete document'
      },
      loadingDocument: 'Loading document…',
      loadError: 'Unable to load this document. Please return to the list and try again.'
    },
    domains: {
      title: 'Domains',
      subtitle: 'Manage domains available for document ingestion.',
      actions: {
        new: 'New Domain'
      },
      table: {
        name: 'Name',
        description: 'Description',
        created: 'Created',
        updated: 'Updated'
      },
      empty: 'No domains found.',
      form: {
        nameLabel: 'Name',
        descriptionLabel: 'Description',
        descriptionPlaceholder: 'Optional description',
        hint: 'Domains are always active once created.',
        validation: {
          nameRequired: 'Name is required.'
        }
      },
      modal: {
        editTitle: 'Edit Domain',
        newTitle: 'New Domain'
      },
      delete: {
        title: 'Delete Domain',
        message: 'Deleting a domain will remove it and any associated documents from the system. This action cannot be undone. Do you still want to proceed?',
        confirm: 'Delete domain'
      },
      toast: {
        loadError: 'Failed to load domains.',
        createSuccess: 'Domain created.',
        createError: 'Failed to create domain.',
        duplicateName: 'A domain with this name already exists. Please choose another name.',
        updateSuccess: 'Domain updated.',
        updateError: 'Failed to update domain.',
        deleteSuccess: 'Domain deleted.',
        deleteError: 'Failed to delete domain.'
      }
    },
    users: {
      title: 'Users',
      subtitle: 'Manage roles, passwords, and access.',
      empty: 'No users found.',
      table: {
        name: 'Name',
        email: 'Email',
        admin: 'Admin',
        updated: 'Updated',
        created: 'Created'
      },
      roles: {
        admin: 'Administrator',
        standard: 'Standard user'
      },
      form: {
        nameLabel: 'Name',
        namePlaceholder: 'Name (optional)',
        nameTooLong: 'Name must be 30 characters or fewer.',
        emailLabel: 'Email',
        emailPlaceholder: 'user@example.com',
        emailRequired: 'Email is required.',
        emailInvalid: 'Enter a valid email address.',
        passwordLabel: 'New password',
        passwordPlaceholder: 'Leave blank to keep current password',
        passwordHint: 'Leave blank to keep the existing password.'
      },
      modal: {
        title: 'Edit {name}'
      },
      delete: {
        message: 'Deleting this user will remove their access immediately. This action cannot be undone. Do you still want to proceed?',
        confirm: 'Delete user',
        button: 'Delete user'
      },
      toast: {
        loadError: 'Failed to load users.',
        updateSuccess: 'User updated.',
        updateError: 'Unable to update user.',
        deleteSuccess: 'User deleted.',
        deleteError: 'Unable to delete user.'
      }
    },
    chat: {
      sidebar: {
        title: 'Conversations',
        new: 'New',
        untitled: 'Untitled conversation',
        editAria: 'Edit conversation',
        edit: 'Edit'
      },
      filter: {
        manage: 'Manage domain filter',
        title: 'Domain filter',
        hint: 'Leave unselected to search across every domain.',
        clearSelection: 'Clear selection',
        apply: 'Apply',
        noConversation: 'Select a conversation to configure domain filters.',
        unavailable: 'Domain filters unavailable.',
        allDomains: 'Filter: All domains',
        applied: 'Filter: {domains}',
        separator: ', ',
        unsaved: 'Unsaved changes — apply to update this conversation',
        status: {
          noConversation: 'Select a conversation to manage domains',
          count: '{count} domain{plural} selected',
          all: 'All domains selected'
        }
      },
      messages: {
        empty: 'No messages yet. Start the conversation by sending a message.',
        you: 'You',
        assistant: 'Assistant',
        system: 'System prompt',
        typing: 'Assistant is typing…'
      },
      composer: {
        placeholder: 'Type your message and press send',
        send: 'Send'
      },
      placeholder: {
        title: 'No conversation selected',
        instructions: 'Choose a conversation from the list or start a new one to begin.',
        empty: 'Create a new conversation to start chatting.'
      },
      new: {
        title: 'Start New Conversation',
        defaultTitle: 'New Conversation',
        nameLabel: 'Conversation Title (optional)',
        namePlaceholder: 'Title (optional)',
        promptLabel: 'Initial Prompt (optional)',
        promptPlaceholder: 'Optional system prompt, e.g., to specify assistant role',
        domainLabel: 'Domain filter (optional)',
        domainHint: 'Pick domains to constrain retrieval. Leave empty to include all domains.',
        start: 'Start Conversation',
        starting: 'Starting…',
        validation: {
          nameRequired: 'Conversation title is required.'
        }
      },
      delete: {
        title: 'Delete Conversation',
        message: 'Are you sure you want to delete this conversation? This action cannot be undone and will remove all messages inside it.',
        confirm: 'Delete conversation'
      },
      edit: {
        title: 'Edit Conversation',
        nameLabel: 'Conversation Title',
        namePlaceholder: 'Title (optional)',
        deleteWarning: 'Deleting this conversation will remove all messages. This action cannot be undone. Continue?'
      },
      errors: {
        notAuthenticated: 'You must be logged in to start a conversation.'
      },
      toast: {
        loadError: 'Unable to load conversations.',
        messagesError: 'Failed to load messages.',
        createSuccess: 'Conversation created.',
        createError: 'Unable to start conversation.',
        sendError: 'Unable to send message.',
        domainApplied: 'Domain filter updated.',
        domainCleared: 'Domain filter cleared.',
        updateSuccess: 'Conversation updated.',
        updateError: 'Unable to update conversation.',
        deleteError: 'Unable to delete conversation.',
        deleteSuccess: 'Conversation deleted.',
        deleteMissing: 'Conversation removed.'
      }
    },
    notFound: {
      title: 'Page not found',
      description: "The page you're looking for doesn't exist.",
      backToDashboard: 'Go back to dashboard'
    },
    Profile: 'Profile'
  }
};
