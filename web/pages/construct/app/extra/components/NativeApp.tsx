/* eslint-disable */
import { apiInterceptors, getAppStrategyValues, getNativeAppScenes, getPromptList, getResource } from '@/client/api';
import AppDefaultIcon from '@/new-components/common/AppDefaultIcon';
import { ParamNeed } from '@/types/app';
import { useRequest } from 'ahooks';
import { Form, InputNumber, Select, Tooltip } from 'antd';
import cls from 'classnames';
import React, { useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import PromptSelect from './auto-plan/PromptSelect';

interface TeamContext {
  scene_name?: string;
  chat_scene?: string;
}
interface InitValueProps {
  team_context: TeamContext;
  param_need: ParamNeed[];
}

interface FormProps {
  chat_scene?: string;
  resources?: string[];
  model?: string;
  temperature?: number;
  max_new_tokens?: number;
  prompt_template?: string;
}

const NativeApp: React.FC<{
  updateData: (data: [boolean, [TeamContext, ParamNeed[]]]) => void;
  classNames?: string;
  initValue?: InitValueProps;
}> = ({ classNames, initValue, updateData }) => {
  const { t } = useTranslation();
  const [form] = Form.useForm<FormProps>();
  const chatScene = Form.useWatch('chat_scene', form);
  const resources = Form.useWatch('resources', form);
  const model = Form.useWatch('model', form);
  const temperature = Form.useWatch('temperature', form);
  const max_new_tokens = Form.useWatch('max_new_tokens', form);
  const prompt_template = Form.useWatch('prompt_template', form);

  const { team_context, param_need } = initValue || {};

  // 获取应用类型&模型
  const { data, loading } = useRequest(async () => {
    const res = await Promise.all([
      apiInterceptors(getNativeAppScenes()),
      apiInterceptors(getAppStrategyValues('priority')),
    ]);
    const [types, models] = res;
    form.setFieldValue('chat_scene', team_context?.chat_scene);
    form.setFieldValue('model', param_need?.find(param => param.type === 'model')?.value);
    form.setFieldValue('temperature', param_need?.find(param => param.type === 'temperature')?.value);
    form.setFieldValue('max_new_tokens', param_need?.find(param => param.type === 'max_new_tokens')?.value);
    form.setFieldValue('prompt_template', param_need?.find(param => param.type === 'prompt_template')?.value);

    const resourceParams = param_need?.filter(param => param.type === 'resource') || [];
    if (resourceParams.length > 0) {
      await run(resourceParams[0].value || '');
    }

    return [types, models] ?? [];
  });

  // 获取prompt提示语列表
  const { data: promptData } = useRequest(async () => {
    const [, res] = await apiInterceptors(
      getPromptList({
        page: 1,
        page_size: 100000,
      }),
    );
    return res ?? { items: [] };
  });

  // 获取资源类型参数列表
  const {
    data: options,
    loading: paramsLoading,
    run,
  } = useRequest(
    async (type: string) => {
      const [, res] = await apiInterceptors(getResource({ type }));
      if (chatScene === team_context?.chat_scene && param_need) {
        const resourceParams = param_need.filter(param => param.type === 'resource');
        if (resourceParams.length > 0) {
          form.setFieldsValue({
            resources: resourceParams.map(param => param.bind_value),
          });
        }
      }

      return (
        res?.map(item => {
          return {
            ...item,
            value: item.key,
          };
        }) ?? []
      );
    },
    { manual: true },
  );

  // 应用类型选项
  const appTypeOptions = useMemo(() => {
    const types = data?.[0]?.[1];
    return (
      types?.map((type: any) => {
        return {
          ...type,
          label: (
            <div className='flex items-center gap-1'>
              <AppDefaultIcon width={4} height={4} scene={type.chat_scene} />
              <Tooltip
                title={`资源类型${type.param_need.filter((param: any) => param.type === 'resource').map((param: any) => param.value || param.label).join(', ')}`}
              >
                <span className='text-[#525964] dark:text-[rgba(255,255,255,0.65)]  ml-1'>{type.scene_name}</span>
              </Tooltip>
            </div>
          ),
          value: type.chat_scene,
        };
      }) || []
    );
  }, [data]);

  // 当前场景的资源需求
  const resourceNeeds = useMemo(() => {
    const currentScene = data?.[0]?.[1]?.find((type: any) => type.chat_scene === chatScene);
    return currentScene?.param_need?.filter((param: any) => param.type === 'resource') || [];
  }, [chatScene, data]);

  // 将数据实时返回给消费组件
  useEffect(() => {
    const rawVal = form.getFieldsValue();
    const currentScene = appTypeOptions.find(type => type.chat_scene === rawVal.chat_scene);

    const params: ParamNeed[] = [
      { type: 'model', value: rawVal.model },
      { type: 'temperature', value: rawVal.temperature },
      { type: 'max_new_tokens', value: rawVal.max_new_tokens },
      { type: 'prompt_template', value: rawVal.prompt_template },
    ];

    if (currentScene) {
      const sceneResourceNeeds = currentScene.param_need.filter((param: any) => param.type === 'resource');
      sceneResourceNeeds.forEach((need: any, index: number) => {
        params.push({
          type: 'resource',
          value: need.value,
          bind_value: rawVal.resources?.[index],
          ...((need as any).label ? { label: (need as any).label } : {}),
        } as ParamNeed);
      });
    }

    updateData([
      loading,
      [
        {
          chat_scene: rawVal.chat_scene,
          scene_name: currentScene?.scene_name,
        },
        params,
      ],
    ]);
  }, [
    form,
    chatScene,
    resources,
    model,
    temperature,
    max_new_tokens,
    prompt_template,
    updateData,
    appTypeOptions,
    loading,
  ]);

  useEffect(() => {
    const type = (data?.[0]?.[1]?.find((type: any) => type.chat_scene === chatScene) as any)?.param_need?.find(
      (param: any) => param.type === 'resource',
    )?.value;
    run(type || '');
  }, [chatScene, data, run]);

  return (
    <div className={cls(classNames)}>
      <Form<FormProps>
        form={form}
        autoComplete='off'
        style={{ width: '100%' }}
        labelCol={{ span: 3 }}
        wrapperCol={{ span: 21 }}
      >
        <Form.Item label={t('native_type')} tooltip name='chat_scene'>
          <Select
            className='w-1/2'
            options={appTypeOptions}
            placeholder={t('app_type_select')}
            onChange={() => form.setFieldsValue({ resources: [] })}
          />
        </Form.Item>
        {chatScene !== 'chat_excel' &&
          resourceNeeds.map((need: any, index: number) => (
            <Form.Item key={index} label={need.label || t('Arguments')} name={['resources', index]}>
              <Select
                placeholder={t('please_select_param')}
                allowClear
                className='w-1/2'
                options={options}
                loading={paramsLoading}
              />
            </Form.Item>
          ))}
        <Form.Item label={t('model')} tooltip name='model'>
          <Select
            placeholder={t('please_select_model')}
            allowClear
            options={data?.[1]?.[1]?.map(item => ({
              label: item,
              value: item,
            }))}
            className='w-1/2'
          />
        </Form.Item>
        <Form.Item label={t('prompt')} name='prompt_template'>
          <PromptSelect promptList={promptData?.items || []} />
        </Form.Item>
        <Form.Item label={t('temperature')} tooltip name='temperature'>
          <InputNumber className='w-1/5 h-8' max={1} min={0} step={0.1} placeholder={t('please_input_temperature')} />
        </Form.Item>
        <Form.Item label={t('max_new_tokens')} tooltip name='max_new_tokens'>
          <InputNumber className='w-1/5 h-8' min={1} placeholder={t('please_input_max_new_tokens')} />
        </Form.Item>
      </Form>
    </div>
  );
};

export default NativeApp;
